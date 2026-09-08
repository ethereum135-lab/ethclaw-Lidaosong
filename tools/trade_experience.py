#!/usr/bin/env python3
"""
trade_experience.py — 每笔卖出复盘 + 经验积累
==============================================
每笔卖出后自动调用，记录：
- 盈利/亏损原因分析
- 触发信号的有效性评估
- 提炼经验值存入总档案

用法：
  python3 tools/trade_experience.py --analyze "SELL|ORCA|50.5|2.094|E2量比0.45x"
  python3 tools/trade_experience.py --daily                     # 生成每日汇总
  python3 tools/trade_experience.py --master                    # 查看总经验档案
"""

import json
import os
import sys
import re as _re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERIENCE_DIR = os.path.join(BASE_DIR, 'data', 'experience')
TRADES_DIR = os.path.join(EXPERIENCE_DIR, 'trades')
DAILY_DIR = os.path.join(EXPERIENCE_DIR, 'daily')
MASTER_FILE = os.path.join(EXPERIENCE_DIR, 'MASTER_EXPERIENCE.json')
TRADE_LOG = os.path.join(BASE_DIR, 'audit', 'TRADES.md')

def load_master():
    try:
        with open(MASTER_FILE) as f:
            return json.load(f)
    except:
        return {"version":"v1.0","rules":[],"stats":{},"exit_signal_performance":{}}

def save_master(master):
    with open(MASTER_FILE, 'w') as f:
        json.dump(master, f, indent=2, ensure_ascii=False)

def extract_trade_info(raw):
    """从原始买入记录提取信息（兼容新旧双管格式）"""
    # Remove backticks (markdown inline code) that interfere with multi-pipe detection
    raw = raw.replace('`', '')
    # Strip emojis that cause column shift in table-format rows
    raw = raw.replace('\U0001f534', '').replace('\U0001f7e2', '').replace('\u26a0\ufe0f', '')
    bg_emoji = ''.join(chr(cp) for cp in range(0x1F7E0, 0x1F7EB))
    for c in bg_emoji:
        raw = raw.replace(c, '')
    parts = [p.strip() for p in raw.split('|')]
    if len(parts) < 4:
        return None

    # 新格式(多重pipe): ||| 或 |||| 或更多 | TIME | OP | SYM | QTY | PRICE | REASON | DATA
    # 中格式(双重pipe): || TIME | OP | SYM | QTY | PRICE | REASON | DATA
    # 旧格式:  | TIME | OP | SYM | QTY | PRICE | REASON | DATA
    if parts[1] == '':
        # 多重pipe: 找第一个非空字段作为time
        start = 1
        while start < len(parts) and parts[start] == '':
            start += 1
        if start >= len(parts) or start + 4 > len(parts):
            # 字段不够（至少需要time+action+symbol+qty+price），退回到单pipe
            start = 1
        idx = {'time': start, 'action': start + 1, 'symbol': start + 2,
               'qty': start + 3, 'price': start + 4, 'reason': start + 5, 'data': start + 6}
    elif parts[0] and not parts[0].startswith(' '):
        # 无前导pipe: time在parts[0]（如"2026-05-06 12:30:03 | SELL | ..."）
        # 新格式: time | SYMBOL | BUY/SELL | qty | price | total | reason
        # 旧格式: time | BUY/SELL | SYMBOL | qty | price | reason | data
        idx = {'time': 0, 'action': 1, 'symbol': 2, 'qty': 3, 'price': 4, 'reason': 5, 'data': 6}
        # Detect new format: if parts[1] is NOT a known action but parts[2] IS
        if len(parts) >= 3:
            p1_upper = parts[1].upper().strip()
            p2_upper = parts[2].upper().strip()
            if p1_upper not in ('BUY', 'SELL') and p2_upper in ('BUY', 'SELL'):
                # Swap action and symbol positions
                idx['action'] = 2
                idx['symbol'] = 1
    else:
        # 单pipe: 有前导pipe，time在parts[1]
        idx = {'time': 1, 'action': 2, 'symbol': 3, 'qty': 4, 'price': 5, 'reason': 6, 'data': 7}

    def safe_get(i):
        return parts[i] if i < len(parts) else ''

    def clean(s):
        return s.replace('**', '').replace('$', '').replace('~', '').replace(',', '').strip()

    # FIX: @-combined qty+price (e.g. '335.8@$0.03762' or '0.036460@$48.9986')
    raw_qty = clean(safe_get(idx['qty']))
    raw_price = clean(safe_get(idx['price']))
    raw_reason = safe_get(idx['reason']) if 'reason' in idx else ''
    # Strip trailing parenthetical total cost like "0.07484 (30.00)" — new TRADES format
    raw_price = _re.sub(r'\s*\([^)]*\)\s*$', '', raw_price).strip()

    import re
    time_val = clean(safe_get(idx['time']))
    action_val = clean(safe_get(idx['action']))

    # Detect table-format rows (| HH:MM | SELL | SYM | QTY | UNIT_PRICE | TOTAL | PNL | REASON |)
    # Real timestamps look like "2026-06-07 15:05:00"
    is_table = False
    if not re.match(r'^\d{4}-\d{2}-\d{2}', time_val):
        # Table format (8 cols): | time | action | symbol | qty | unit_price | total_cost | pnl | reason |
        # Pipe format (7 cols):  | time | action | symbol | qty | price      | reason      | data |
        # Difference: total_cost (idx+5) and pnl (idx+6) inserted between price (idx+4) and reason (idx+7)
        is_table = True
        time_real = 'TABLE_ROW'
        # Adjust indices for table format: skip total_cost and pnl columns
        idx['reason'] = idx.get('data', idx.get('reason', 0)) + 1  # jump past pnl to real reason
        if 'data' in idx:
            idx['data'] = idx['reason'] + 1
        # Re-extract raw_price with table-aware clean (already done above, OK)

    # Detect total_cost column between price and reason (7-col format: qty, unit_price, total_cost, reason)
    # Only for non-table rows — table rows already have correct indices set above
    if not is_table:
        reason_guess = clean(safe_get(idx['reason']))
        raw_data_val = safe_get(idx['data']) if 'data' in idx else ''
        data_clean_val = clean(raw_data_val)
        if reason_guess and data_clean_val:
            dollar_like = bool(_re.match(r'^\$?[0-9]+\.?[0-9]*$', reason_guess))
            if dollar_like and '$' in raw_price and not raw_price.startswith('$'):
                # Already @-combined, don't double-shift
                pass
            elif dollar_like:
                # 'reason' is actually total_cost -> swap; data becomes the real reason
                idx['reason'] = idx['data']
                idx['data'] = idx['reason'] + 1 if idx.get('data') else idx.get('data')

    if '@' in raw_qty:
        parts_at = raw_qty.split('@', 1)
        raw_qty = parts_at[0].strip()
        raw_price = parts_at[1].strip()
        # Strip trailing parenthetical total cost like "0.07484 (30.00)"
        raw_price = clean(raw_price)
        raw_price = _re.sub(r'\s*\([^)]*\)\s*$', '', raw_price).strip()
        # When qty contains @, the next field is actually the reason, not price
        idx['reason'] = idx['price']

    return {
        'time': time_real if is_table else time_val,
        'action': action_val,
        'symbol': clean(safe_get(idx['symbol'])),
        'qty': raw_qty,
        'price': raw_price,
        'reason': clean(safe_get(idx['reason'])),
        'data': clean(safe_get(idx['data'])),
        'is_table_format': is_table,
    }

def get_last_exit(symbol=None):
    """从交易记录获取最近一次卖出的详情（及其对应的买入）"""
    try:
        with open(TRADE_LOG) as f:
            lines = f.readlines()
    except:
        return None
    
    # 找最后一次卖出（兼容 **SELL**、**SELL SYM**、🔴SELL、🔴 SELL、🟢SELL 等格式）
    sells = []
    for line in lines:
        stripped = line.replace('**', '').replace('🔴 ', '').replace('🔴', ' ').replace('🟢 ', '').replace('🟢', ' ').replace('⚠️', '')
        parts_check = [p.strip() for p in stripped.split('|')]
        # Check both exact 'SELL' match and 'SELL SYM' prefix match (new node_check format: | **SELL XPL** | ...)
        has_sell = 'SELL' in parts_check or any(p.startswith('SELL ') for p in parts_check)
        if has_sell and 'NO TRADE' not in stripped:
            info = extract_trade_info(line)
            # 过滤噪声行：表头行（"操作"作时间）、空symbol、空price
            if info and info.get('symbol') and info.get('price', '').replace('.', '').replace('-', '').strip():
                if symbol is None or info['symbol'] == symbol:
                    sells.append(info)
    
    if not sells:
        return None
    
    # Filter out table-format rows (is_table_format=True) — they have no real timestamp
    sells = [s for s in sells if not s.get('is_table_format', False)]
    
    # Filter out placeholder price rows ($0.0000 from pipeline format)
    sells = [s for s in sells if not s.get('price', '').replace('$','').strip() in ('0.0000', '0', '0.0')]
    
    if not sells:
        return None
    
    # 按时间排序，取最新卖出 (TRADES.md新交易在顶部，旧交易在底部)
    last_sell = max(sells, key=lambda x: x['time'])
    
    # 找对应买入：同一币种在卖出前 **最近一次** 买入（按时间取max）
    buys = []
    for line in lines:
        stripped = line.replace('**', '').replace('🔴 ', '').replace('🔴', ' ').replace('🟢 ', '').replace('🟢', ' ').replace('⚠️', '')
        parts_check = [p.strip() for p in stripped.split('|')]
        has_buy = 'BUY' in parts_check or any(p.startswith('BUY ') for p in parts_check)
        if has_buy and 'NO TRADE' not in stripped:
            info = extract_trade_info(line)
            if info and info['symbol'] == last_sell['symbol'] and info['time'] < last_sell['time']:
                buys.append(info)
    
    buy = max(buys, key=lambda x: x['time']) if buys else None
    
    return {'sell': last_sell, 'buy': buy}

def analyze_exit(sell_info, buy_info):
    """分析一笔卖出的盈亏和信号有效性"""
    import re
    sell_price = float(sell_info['price']) if buy_info else 0
    sell_qty = float(sell_info['qty']) if buy_info else 0
    
    # Extract accurate prices from reason field (入场→出场 format) if available
    reason = sell_info.get('reason', '')
    sell_reason_price = None
    buy_reason_price = None
    sell_match = re.search(r'出场[：: ]*\$?([0-9.]+)', reason)
    if sell_match:
        sell_reason_price = float(sell_match.group(1))
    buy_match = re.search(r'入场[：: ]*\$?([0-9.]+)', reason)
    if buy_match:
        buy_reason_price = float(buy_match.group(1))
    
    # Resolve actual buy unit price (handles old vs new TRADES format):
    #   Old format: col5 = unit_price (e.g., $0.10697 for DOGE)
    #   New format: col5 = total_cost (e.g., $5.999 for RONIN, unit=$0.1242)
    buy_price_raw = float(buy_info['price']) if buy_info else 0
    buy_qty = float(buy_info['qty']) if buy_info else 0
    buy_price = buy_price_raw
    effective_qty = buy_qty  # token count for P&L calc (from sell, since sell may be partial)
    
    # Use buy reason price if available (more reliable than column parsing)
    if buy_reason_price and buy_reason_price > 0:
        buy_price = buy_reason_price
    
    # Detect sell row format where col4=unit_price, col5=total_value
    # (inconsistent with buy row format col4=qty, col5=unit_price)
    if sell_reason_price and sell_reason_price > 0:
        # The reason field explicitly states the sell unit price
        sell_price = sell_reason_price
        # Compute effective qty: if total_value (col5) / unit_price ≈ reasonable qty, use it
        total_val = float(sell_info['price'])
        if total_val > sell_price * 2:  # col5 is total_value, not unit price
            sell_qty = total_val / sell_price
        elif float(sell_info['qty']) > total_val:  # col4 is qty (normal format)
            sell_qty = float(sell_info['qty'])
    elif sell_price > 0 and buy_price > 0:
        # Heuristic: if parsed sell price (col5) >> buy_price and parsed qty (col4) ≈ buy_price, swap
        parsed_qty = sell_qty  # col4
        parsed_price = sell_price  # col5
        if 0 < buy_price < parsed_price * 0.5 and parsed_qty > 0 and parsed_price / parsed_qty > 5:
            # col4 likely unit_price, col5 likely total_value
            sell_price = parsed_qty  # col4 is actually unit price
            sell_qty = parsed_price / parsed_qty  # qty = total / unit
    
    if buy_price_raw > 0 and buy_qty > 0:
        # Try detecting new format: col5 = total_cost instead of unit_price
        # Compare both interpretations against sell_price to pick the correct one.
        #   Scenario A: buy_price_raw IS the unit price.
        #   Scenario B: buy_price_raw is total_cost → unit = buy_price_raw / buy_qty
        # Pick the interpretation whose unit price is closer to sell_price.
        if sell_price > 0 and buy_price_raw >= 5 * sell_price:
            buy_price = buy_price_raw / buy_qty  # unit_price = total_cost / qty
        elif buy_price_raw > 50 and buy_qty > 0:
            unit_if_raw = buy_price_raw
            unit_if_total = buy_price_raw / buy_qty
            delta_raw = abs(unit_if_raw - sell_price) / sell_price
            delta_total = abs(unit_if_total - sell_price) / sell_price
            # Pick whichever unit price is closer to sell_price
            if delta_raw <= delta_total:
                buy_price = unit_if_raw
            else:
                buy_price = unit_if_total
    
    result = {
        'symbol': sell_info['symbol'],
        'sell_time': sell_info['time'],
        'buy_time': buy_info['time'] if buy_info else '未知',
        'sell_price': sell_price,
        'buy_price': buy_price,
        'exit_reason': sell_info['reason'],
        'qty': sell_qty,
        'buy_qty_raw': buy_qty,  # diagnostic
        'buy_price_raw': buy_price_raw,  # diagnostic
    }
    
    if buy_price > 0:
        result['pnl_pct'] = (sell_price - buy_price) / buy_price * 100
        result['pnl_usd'] = sell_qty * (sell_price - buy_price)
    else:
        result['pnl_pct'] = 0
        result['pnl_usd'] = 0
    
    # 提取触发信号
    reason = sell_info['reason']
    signals = []
    for sig in ['E1', 'E2', 'E3', 'E4', 'E5', 'E6']:
        if sig in reason:
            signals.append(sig)
    # P系列信号检测（陷阱21修复）
    if 'P1' in reason or 'RSI' in reason and ('超买' in reason or 'overbought' in reason.lower()):
        signals.append('P1')
    if 'P3' in reason or '趋势衰竭' in reason:
        signals.append('P3')
    result['trigger_signals'] = signals
    
    # P1盈利时标记为correct（覆盖纯P&L阈值判断）
    if 'P1' in signals and result['pnl_pct'] > 0:
        result['exit_quality'] = 'correct'
        result['lesson'] = f"P1 RSI超买止盈（已验证100%胜率）{result['symbol']}+{result['pnl_pct']:.1f}%"
    elif 'P1' in signals and result['pnl_pct'] <= 0:
        result['exit_quality'] = 'neutral'
        result['lesson'] = f"P1 RSI超买中性退出（持仓成本较高）{result['pnl_pct']:+.1f}%"
    
    # 评估信号有效性（卖完后的判断基于历史验证）
    if result['pnl_pct'] >= 2.99:
        result['exit_quality'] = 'correct'  # 卖得对，赚了
        result['lesson'] = f"{result['symbol']}卖在盈利位(+{result['pnl_pct']:.1f}%)，信号有效"
    elif result['pnl_pct'] > -1:
        result['exit_quality'] = 'neutral'  # 平进平出，基本持平
        result['lesson'] = f"{result['symbol']}平进平出({result['pnl_pct']:+.1f}%)，E2/E3可能误触"
    else:
        result['exit_quality'] = 'wrong'  # 亏了
        result['lesson'] = f"{result['symbol']}亏损{result['pnl_pct']:.1f}%，退出信号过早"
    
    return result

def record_trade_experience(analysis):
    """将单笔经验存入交易级文件 + 更新总档案"""
    # 检查是否已分析过 (防重复)
    ts = analysis['sell_time'].replace(' ', '_').replace(':', '-')
    filename = f"{ts}_{analysis['symbol']}.json"
    trade_file = os.path.join(TRADES_DIR, filename)
    
    if os.path.exists(trade_file):
        # 已分析过，更新master以防之前有重复，但不重新写入
        return None
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'analysis': analysis
    }
    
    with open(trade_file, 'w') as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)
    
    # 更新总档案
    master = load_master()
    master['stats']['total_trades_analyzed'] = master['stats'].get('total_trades_analyzed', 0) + 1
    
    if analysis['exit_quality'] == 'correct':
        master['stats']['correct_exits'] = master['stats'].get('correct_exits', 0) + 1
    elif analysis['exit_quality'] == 'wrong':
        master['stats']['wrong_exits'] = master['stats'].get('wrong_exits', 0) + 1
    else:
        master['stats']['too_early_exits'] = master['stats'].get('too_early_exits', 0) + 1
    
    # 信号表现统计
    for sig in analysis['trigger_signals']:
        if sig not in master['exit_signal_performance']:
            master['exit_signal_performance'][sig] = {'total': 0, 'correct': 0, 'wrong': 0, 'neutral': 0}
        perf = master['exit_signal_performance'][sig]
        perf['total'] += 1
        if analysis['exit_quality'] == 'correct':
            perf['correct'] += 1
        elif analysis['exit_quality'] == 'wrong':
            perf['wrong'] += 1
        else:
            perf['neutral'] += 1
    
    # 提取经验规则 (使用指纹去重)
    if analysis['pnl_pct'] > 0 and 'E2' in analysis['trigger_signals']:
        rule = {
            'signal': 'E2',
            'condition': '成交量萎缩 且 趋势转跌或费率回归',
            'effectiveness': '有效',
            'verified_by': analysis['symbol']
        }
        fp = f"E2|成交量萎缩 且 趋势转跌或费率回归|有效|{analysis['symbol']}"
        if not any(f"{r.get('signal','')}|{r.get('condition','')}|{r.get('effectiveness','')}|{r.get('verified_by','')}" == fp for r in master['rules']):
            master['rules'].append(rule)
    
    if analysis['pnl_pct'] < -1:
        # Avoid rule bloat: only add 1 loss rule per symbol per 30 days
        same_sym_recent = any(
            r.get('condition', '').startswith(f"{analysis['symbol']}在")
            and datetime.now().isoformat()[:7] == master.get('last_updated', '')[:7]
            for r in master['rules']
        )
        if not same_sym_recent:
            rule = {
                'signal': '+'.join(analysis['trigger_signals']),
                'condition': f"{analysis['symbol']}在{analysis['buy_price']:.4f}买入,{analysis['sell_price']:.4f}卖出",
                'effectiveness': '需要改进',
                'pnl': f"{analysis['pnl_pct']:.1f}%"
            }
            fp = f"{rule['signal']}|{rule['condition']}|{rule['effectiveness']}"
            if not any(f"{r.get('signal','')}|{r.get('condition','')}|{r.get('effectiveness','')}" == fp for r in master['rules']):
                master['rules'].append(rule)
    
    master['last_updated'] = datetime.now().isoformat()
    save_master(master)
    
    return entry
def generate_daily_summary(date_str=None):
    """生成每日经验汇总"""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    files = [f for f in os.listdir(TRADES_DIR) if f.startswith(date_str)]
    
    if not files:
        return f"  [{date_str}] 今日无卖出交易分析"
    
    summary_lines = [f"## {date_str} 卖出复盘汇总"]
    summary_lines.append(f"\n今日共 {len(files)} 笔卖出\n")
    
    correct = 0
    wrong = 0
    total_pnl = 0
    
    for fname in sorted(files):
        with open(os.path.join(TRADES_DIR, fname)) as f:
            entry = json.load(f)
        a = entry['analysis']
        icon = '✅' if a['exit_quality'] == 'correct' else ('❌' if a['exit_quality'] == 'wrong' else '➖')
        summary_lines.append(f"  {icon} {a['symbol']:8s} {a['exit_reason'][:40]:40s} P&L: {a['pnl_pct']:+.1f}%  |  {a['lesson']}")
        
        if a['exit_quality'] == 'correct':
            correct += 1
        elif a['exit_quality'] == 'wrong':
            wrong += 1
        total_pnl += a['pnl_usd']
    
    summary_lines.append(f"\n  正确: {correct} | 错误: {wrong} | 总盈亏: ${total_pnl:+.2f}")
    
    # 保存每日汇总
    daily_file = os.path.join(DAILY_DIR, f"{date_str}.md")
    with open(daily_file, 'w') as f:
        f.write('\n'.join(summary_lines))
    
    return '\n'.join(summary_lines)

def show_master():
    """查看总经验档案"""
    master = load_master()
    lines = ["=== 总经验档案 ==="]
    lines.append(f"分析交易数: {master['stats'].get('total_trades_analyzed', 0)}")
    lines.append(f"正确退出: {master['stats'].get('correct_exits', 0)}")
    lines.append(f"错误退出: {master['stats'].get('wrong_exits', 0)}")
    lines.append(f"中性退出: {master['stats'].get('too_early_exits', 0)}")
    
    lines.append(f"\n--- 信号表现 ---")
    for sig, perf in sorted(master.get('exit_signal_performance', {}).items()):
        rate = perf['correct'] / perf['total'] * 100 if perf['total'] > 0 else 0
        lines.append(f"  {sig}: {perf['total']}次触发, 正确率{rate:.0f}%")
    
    lines.append(f"\n--- 已验证经验规则 ---")
    for rule in master.get('rules', [])[-5:]:
        lines.append(f"  信号{rule['signal']} + {rule.get('condition','')} = {rule['effectiveness']}")
    
    return '\n'.join(lines)

def cli():
    if len(sys.argv) < 2:
        print("用法:")
        print("  --analyze \"SELL|ORCA|50|2.09|E2量比\"  分析一笔卖出")
        print("  --daily                              今日汇总")
        print("  --daily YYYY-MM-DD                   指定日期汇总")
        print("  --master                             总档案")
        return
    
    if '--analyze' in sys.argv:
        idx = sys.argv.index('--analyze') + 1
        if idx < len(sys.argv):
            raw = sys.argv[idx]
            result = get_last_exit()
            if result and result['sell']:
                analysis = analyze_exit(result['sell'], result['buy'])
                entry = record_trade_experience(analysis)
                print(json.dumps(analysis, indent=2, ensure_ascii=False))
            else:
                print("未找到卖出记录")
    
    if '--daily' in sys.argv:
        idx = sys.argv.index('--daily') + 1
        date_str = sys.argv[idx] if idx < len(sys.argv) and not sys.argv[idx].startswith('--') else None
        print(generate_daily_summary(date_str))
    
    if '--master' in sys.argv:
        print(show_master())

if __name__ == '__main__':
    cli()
