#!/usr/bin/env python3
"""
每笔交易复盘工具 v2 — 2026-06-12 修复
- 兼容任意数量前导竖线（7-11个）
- 提取 just_starting+7.3% 格式的入场动量
- 提取 STRONG102 / conf=10 信号分
- 精确提取 PnL（profit $X.XX / 利润($X.XX) / 释放$X.XX）
- 改进方向区有数据支撑，不空着
"""
import json, os, sys, re
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter

BJT = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES_PATH = os.path.join(BASE_DIR, "audit", "TRADES.md")
REVIEW_DIR = os.path.join(BASE_DIR, "data", "reviews")

# ─── 解析TRADES.md ───

def _extract_pnl_and_scores(entry):
    """从reason提取入场动量、信号分和P&L"""
    reason = entry.get('reason', '')
    result = {}
    
    # 提取入场动量：just_starting+7.3% / 刚启动+7.3% / trending+5.2% / gain_24h=7.3%
    gain_m = re.search(r'(?:just_starting|刚启动|trending|gain_24h)[=+]+([\d.]+)%', reason)
    if gain_m:
        result['gain_24h'] = float(gain_m.group(1))
    # 兜底：frEntry+16.6% 或 entry/+5%
    if 'gain_24h' not in result:
        gain_m2 = re.search(r'(?:frEntry|entry/)[+](\d+[.]?\d*)%', reason)
        if gain_m2:
            result['gain_24h'] = float(gain_m2.group(1))
    
    # 提取信号分：STRONG102 / SIGNAL47 / conf=10 / conf9
    score_m = re.search(r'(?:STRONG|SIGNAL|WATCH)\s*(\d+)', reason)
    if score_m:
        result['score'] = int(score_m.group(1))
    if 'score' not in result:
        conf_m = re.search(r'conf[=]?(\d+)', reason)
        if conf_m:
            result['score'] = int(conf_m.group(1)) * 10  # conf9→90分
    
    # 提取P&L — 优先从SELL理由精确提取
    # profit $X.XX
    pnl_usd_m2 = re.search(r'profit\s+\$([\d.]+)', reason)
    if pnl_usd_m2:
        result['pnl_usd'] = float(pnl_usd_m2.group(1))
    # 利润($X.XX)
    pnl_usd_m3 = re.search(r'利润\(?\$([\d.]+)\)?', reason)
    if pnl_usd_m3:
        result['pnl_usd'] = float(pnl_usd_m3.group(1))
    # 释放$X.XX
    pnl_usd_m4 = re.search(r'释放\$([\d.]+)', reason)
    if pnl_usd_m4:
        result['pnl_usd'] = float(pnl_usd_m4.group(1))
    # 兜底：SELL理由中"回收资金"后的金额
    if 'pnl_usd' not in result:
        recycle_m = re.search(r'回收资金\s*\$?([\d.]+)', reason)
        if recycle_m:
            result['pnl_usd'] = float(recycle_m.group(1))
    # Swap理由中的成交金额（Swap_to_XX...FILLED）
    if 'pnl_usd' not in result and entry.get('action') == 'SELL':
        # Swap卖出：提取卖出金额
        swap_sell = re.search(r'SELL\s+[\d.]+\s+@\s+\$?([\d.]+)\s*=\s*\$?([\d.]+)', reason, re.IGNORECASE)
        if swap_sell:
            result['pnl_usd'] = float(swap_sell.group(2))
    # 兜底：SELL理由中的 "$X.XX" 或 "exception<$X" 金额
    if 'pnl_usd' not in result and entry.get('action') == 'SELL':
        any_usd = re.search(r'[<$]\$?([\d.]+)', reason)
        if any_usd:
            result['pnl_usd'] = float(any_usd.group(1))
    # 最终兜底：reason末尾的 $X.XX
    if 'pnl_usd' not in result:
        pnl_usd_m = re.search(r'\$([\d.]+)\s*$', reason)
        if pnl_usd_m:
            result['pnl_usd'] = float(pnl_usd_m.group(1))
    
    # PnL百分比：紧跟在profit/利润前的百分比
    pnl_m = re.search(r'([+-]?[\d.]+)%\s*(?:profit|利润)', reason)
    if pnl_m:
        result['pnl_pct'] = float(pnl_m.group(1))
    
    # Swap换仓理由中的PnL%: worst_PnL_RE_-2.28%  或 MEGA_-0.37%
    if 'pnl_pct' not in result:
        swap_pnl = re.search(r'worst_PnL_\w+_([+-]?[\d.]+)%', reason)
        if swap_pnl:
            result['pnl_pct'] = float(swap_pnl.group(1))
    
    return result


def parse_trades(text):
    """从TRADES.md提取BUY和SELL交易"""
    buys = []
    sells = []
    
    # 管道格式 — 匹配任意数量前导竖线
    pipe_pattern = re.compile(
        r'[|]+\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s*\|\s*(BUY|SELL)\s*\|\s*(\w+)\s*\|\s*([\d.]+)\s*\|\s*\$?([\d.]+)\s*\|\s*(.*)'
    )
    # 无前导竖线格式：ts | BUY/SELL | SYMBOL | qty | price | value 或 ts | SYMBOL | BUY/SELL | qty | price | value
    bare_pattern = re.compile(
        r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s*\|\s*(?:(BUY|SELL)\s*\|\s*(\w+)|(\w+)\s*\|\s*(BUY|SELL))\s*\|\s*([\d.]+)\s*\|\s*\$?([\d.]+)\s*\|\s*\$?([\d.]+)\s*\|\s*(.*)',
        re.MULTILINE
    )
    
    for m in pipe_pattern.finditer(text):
        ts = m.group(1)
        if len(ts) == 16:
            ts += ":00"
        action = m.group(2)
        symbol = m.group(3)
        qty = float(m.group(4))
        price = float(m.group(5))
        reason = m.group(6).strip()
        
        entry = {
            'ts': ts,
            'action': action,
            'symbol': symbol,
            'qty': qty,
            'price': price,
            'reason': reason,
        }
        entry.update(_extract_pnl_and_scores(entry))
        
        if action == 'BUY':
            buys.append(entry)
        else:
            sells.append(entry)
    
    for m in bare_pattern.finditer(text):
        ts = m.group(1)
        if len(ts) == 16:
            ts += ":00"
        # 判断是 (BUY|SELL)|symbol 还是 symbol|(BUY|SELL)
        action = m.group(2) or m.group(5)
        symbol = m.group(3) or m.group(4)
        qty = float(m.group(6))
        price = float(m.group(7))
        value = m.group(8)
        reason = m.group(9).strip()
        
        entry = {
            'ts': ts,
            'action': action,
            'symbol': symbol,
            'qty': qty,
            'price': price,
            'value': float(value) if value else None,
            'reason': reason,
        }
        entry.update(_extract_pnl_and_scores(entry))
        
        if action == 'BUY':
            buys.append(entry)
        else:
            sells.append(entry)
    
    return buys, sells


def calculate_gain_tier(gain_pct):
    """根据gain_24h判断分档"""
    if gain_pct is None:
        return "未知"
    if gain_pct >= 50:
        return "🔴追高>50%"
    elif gain_pct >= 20:
        return "🟡中动量20-50%"
    elif gain_pct >= 5:
        return "🟢低动量5-20%"
    else:
        return "⚪微动量<5%"

def assess_entry(symbol, buy_info):
    """评估入场决策质量"""
    findings = []
    
    gain = buy_info.get('gain_24h', None)
    score = buy_info.get('score', None)
    
    if gain is not None:
        tier = calculate_gain_tier(gain)
        if gain >= 50:
            findings.append("❌ 追高风险（gain≥50%，不该买入）")
        elif gain >= 20:
            findings.append(f"⚠️ 中等风险（gain={gain:.1f}%，减半仓正确）")
        elif gain >= 5:
            findings.append(f"✅ 健康动量（gain={gain:.1f}%<20%，正常仓位合理）")
        else:
            findings.append(f"✅ 低动量入场（gain={gain:.1f}%<5%，安全但需确认趋势）")
    
    if score is not None:
        if score >= 80:
            findings.append(f"✅ STRONG{score}分（信号充足）")
        elif score >= 50:
            findings.append(f"⚠️ 信号{score}分（中等，需验证）")
        else:
            findings.append(f"⚠️ 弱信号{score}分（谨慎）")
    
    if not findings:
        # 从reason提取有用信息
        reason = buy_info.get('reason', '')
        if '极恐试探' in reason:
            findings.append("⚠️ 极恐试探模式入场（F&G极低，高风险高回报）")
        elif '轮换' in reason or '轮入' in reason:
            findings.append("🔄 轮换入场（资金再分配）")
        elif 'BUY_READY' in reason:
            findings.append("✅ BUY_READY信号入场")
        elif 'ZH手动' in reason:
            findings.append("👤 ZH手动操作入场")
        else:
            findings.append("数据不足")
    
    return "; ".join(findings)

def assess_exit(sell_info, buy_info):
    """评估出场决策质量"""
    findings = []
    
    pnl_pct = sell_info.get('pnl_pct', None)
    pnl_usd = sell_info.get('pnl_usd', None)
    reason = sell_info.get('reason', '')
    
    if pnl_pct is not None:
        if pnl_pct > 3:
            findings.append(f"✅ 盈利出场+{pnl_pct:.1f}%")
            if '止盈' in reason or 'T1' in reason or 'T2' in reason:
                findings.append("✅ 按计划止盈")
        elif pnl_pct > 0:
            findings.append(f"✅ 微盈出场+{pnl_pct:.1f}%")
        elif pnl_pct <= -3:
            findings.append(f"❌ 亏损出场{pnl_pct:.1f}%")
        else:
            findings.append(f"⚪ 微亏出场{pnl_pct:.1f}%")
    
    # 出场理由判断
    if '尘仓' in reason or 'dust' in reason.lower():
        findings.append("🧹 尘仓清理（释放资金，正确操作）")
    if '轮换' in reason or '轮出' in reason:
        findings.append("🔄 轮换出场（资金再分配）")
    if '最弱' in reason or '弱' in reason:
        findings.append("📉 最弱持仓出场（优化仓位）")
    if 'volume_collapse' in reason.lower() or '成交量' in reason:
        findings.append("📊 成交量萎缩出场（技术信号）")
    if 'ZH手动' in reason:
        findings.append("👤 ZH手动操作出场")
    
    if not findings:
        findings.append("数据不足")
    
    return "; ".join(findings)

def review_pairs(buys, sells):
    """将BUY和SELL配对，输出逐笔复盘"""
    reviews = []
    
    # 按币种分组
    by_symbol = defaultdict(list)
    for s in sells:
        by_symbol[s['symbol']].append(s)
    
    # 为每个SELL找对应的BUY
    for symbol, sell_list in by_symbol.items():
        symbol_buys = sorted(
            [b for b in buys if b['symbol'] == symbol],
            key=lambda x: x['ts']
        )
        
        for s in sorted(sell_list, key=lambda x: x['ts']):
            # 找到最近的买入
            best_buy = None
            for b in reversed(symbol_buys):
                if b['ts'] <= s['ts']:
                    best_buy = b
                    break
            
            review = {
                'symbol': symbol,
                'sell_ts': s['ts'],
                'sell_reason': s['reason'],
                'sell_pnl': s.get('pnl_pct', None),
                'sell_pnl_usd': s.get('pnl_usd', None),
            }
            
            if best_buy:
                review['buy_ts'] = best_buy['ts']
                review['buy_reason'] = best_buy['reason']
                review['gain_24h'] = best_buy.get('gain_24h', None)
                review['score'] = best_buy.get('score', None)
                review['entry_assessment'] = assess_entry(symbol, best_buy)
            else:
                review['buy_ts'] = '未知'
                review['buy_reason'] = '旧仓或数据缺失'
                review['entry_assessment'] = '旧仓，无法回溯'
            
            review['exit_assessment'] = assess_exit(s, best_buy or {})
            review['gain_tier'] = calculate_gain_tier(review.get('gain_24h'))
            
            reviews.append(review)
    
    return reviews

# ─── 总权益提取 ───

def extract_equity_totals(text):
    """从TRADES.md提取总权益（第一笔=昨日收盘，最后一笔=当前）
    只匹配时间序列中的总权益/总账户估计（跳过文件头部的宏观信息）"""
    total_current = None
    yesterday_close = None
    
    # 先找到今天的第一个时间序列开始
    today_str = datetime.now(BJT).strftime('%Y-%m-%d')
    today_start = text.find(f"## 节点时间：{today_str}")
    if today_start == -1:
        today_start = text.find(f"### {today_str}")
    if today_start == -1:
        today_start = text.rfind("### 2026")
    if today_start == -1:
        today_start = 0
    
    body = text[today_start:]
    
    # 格式: "**总权益:** ~$232.05" 或 "总账户估计 | ~$232.85"
    today_matches = re.findall(r'(?:总权益|总账户估计)[^$]*~?\$?([\d.]+)', body)
    
    if today_matches:
        total_current = float(today_matches[-1])
        # 昨日收盘 = 今天第一条（当日01:00的第一个点）
        yesterday_close = float(today_matches[0])
    
    return total_current, yesterday_close


def generate_trade_tip(reviews):
    """生成改进建议"""
    tips = []
    
    if not reviews:
        tips.append("今天无卖出交易。")
        return tips
    
    # 1. 按出场理由统计
    exit_reasons = Counter()
    for rv in reviews:
        reason = rv['sell_reason']
        if '尘仓' in reason or 'dust' in reason.lower():
            exit_reasons['尘仓清理'] += 1
        elif '轮换' in reason or '轮出' in reason:
            exit_reasons['轮换/轮出'] += 1
        elif 'ZH' in reason and '手动' in reason:
            exit_reasons['ZH手动操作'] += 1
        elif '止损' in reason:
            exit_reasons['止损'] += 1
        else:
            exit_reasons['其他'] += 1
    
    dominant_reason = exit_reasons.most_common(1)[0][0]
    if dominant_reason == '轮换/轮出':
        tips.append("🔄 多数交易为轮换出场。检查轮入的币是否涨幅更好，确认轮换策略有效。")
    elif dominant_reason == '尘仓清理':
        tips.append("🧹 多次尘仓清理。考虑提高最低开仓金额，减少需要频繁清理的小仓位。")
    elif dominant_reason == 'ZH手动操作':
        tips.append("👤 ZH手动干预频繁。评估系统自动判断与人工干预的协同效率。")
    
    # 2. 信号分分析
    scored_trades = [rv for rv in reviews if rv.get('score') is not None]
    if scored_trades:
        avg_score = sum(rv['score'] for rv in scored_trades) / len(scored_trades)
        if avg_score < 60:
            tips.append(f"📊 平均信号分{avg_score:.0f}偏低，入场标准可能偏宽松。")
        elif avg_score > 90:
            tips.append(f"📊 平均信号分{avg_score:.0f}较高，入场标准偏严。")
    
    # 3. 动量分析（仅当有数据时）
    gain_trades = [rv for rv in reviews if rv.get('gain_24h') is not None]
    if gain_trades:
        avg_gain = sum(rv['gain_24h'] for rv in gain_trades) / len(gain_trades)
        if avg_gain > 20:
            tips.append(f"⚠️ 平均入场动量{avg_gain:.1f}%偏高，大部分买入在涨幅已较大时入场。")
        elif avg_gain < 5:
            tips.append(f"✅ 平均入场动量{avg_gain:.1f}%偏低，在低涨幅时入场较为安全。")
    
    # 4. 入场方式分析
    terror_trades = [rv for rv in reviews if '极恐' in rv.get('buy_reason', '')]
    if terror_trades:
        tips.append(f"🐻 {len(terror_trades)}笔来自极恐试探模式（F&G极低），关注极恐模式胜率。")
    
    # 5. 微亏微盈分析（轮换过多提示）
    small_trades = [rv for rv in reviews 
                    if rv.get('sell_pnl') is not None and abs(rv['sell_pnl']) < 1.5
                    and ('轮换' in rv['sell_reason'] or '轮出' in rv['sell_reason'])]
    if len(small_trades) >= 3:
        tips.append(f"🔄 {len(small_trades)}笔轮换交易盈利在±1.5%以内。频繁小轮换消耗手续费，建议降低轮换频率。")
    
    if not tips:
        tips.append("交易模式较多样化，持续观察。")
    
    return tips


def print_review(reviews, date_label, total_current=None, yesterday_close=None):
    """输出复盘报告"""
    lines = []
    lines.append(f"# 📊 逐笔交易复盘 — {date_label}\n")
    
    if not reviews:
        lines.append("今天无卖出交易（换仓/轮换不计入卖出流水）。\n")

    if not reviews and total_current is not None and yesterday_close is not None:
        net_change = total_current - yesterday_close
        net_pct = (net_change / yesterday_close) * 100 if yesterday_close > 0 else 0
        emoji = "✅" if net_change >= 0 else "❌"
        # 插入头部
        head = f"**{emoji} 真·日盈亏：${total_current:.2f} - ${yesterday_close:.2f} = ${net_change:+.2f} ({net_pct:+.1f}%)**\n"
        return head + "\n" + "\n".join(lines)

    if not reviews:
        return "\n".join(lines)
    
    # 双重口径
    sell_pnl_total = 0
    win = 0
    loss = 0
    neutral = 0
    
    for rv in reviews:
        pnl = rv.get('sell_pnl_usd', 0) or rv.get('sell_pnl', 0)
        if isinstance(pnl, (int, float)):
            if pnl > 0:
                win += 1
            elif pnl < 0:
                loss += 1
            else:
                neutral += 1
            if rv.get('sell_pnl_usd'):
                sell_pnl_total += rv['sell_pnl_usd']
    
    # 总权益变化（真·净利）
    net_change = None
    if total_current is not None and yesterday_close is not None:
        net_change = total_current - yesterday_close
        net_pct = (net_change / yesterday_close) * 100 if yesterday_close > 0 else 0
    
    # 报告头部：双口径
    if net_change is not None:
        emoji = "✅" if net_change >= 0 else "❌"
        lines.append(f"**{emoji} 真·日盈亏：${total_current:.2f} - ${yesterday_close:.2f} = ${net_change:+.2f} ({net_pct:+.1f}%)**")
        lines.append(f"   └ 卖出流水：+${sell_pnl_total:.2f} (已实现) | 目标+0.2%=${yesterday_close*0.002:.2f}")
        lines.append(f"   └ 持仓变动：新仓浮亏抵消了卖出利润（总权益从${yesterday_close:.2f}→${total_current:.2f}）")
    else:
        lines.append(f"**汇总：** {len(reviews)}笔卖出 | ✅正确{win} ❌错误{loss} ➖中性{neutral} | 净利${sell_pnl_total:.2f}\n")
    
    for i, rv in enumerate(reviews, 1):
        lines.append(f"### 交易 #{i}: {rv['symbol']}\n")
        lines.append(f"| 维度 | 详情 |")
        lines.append(f"|:----|:-----|")
        lines.append(f"| 卖出时间 | {rv['sell_ts']} |")
        lines.append(f"| 入场时间 | {rv['buy_ts']} |")
        pnl = rv.get('sell_pnl')
        pnl_str = f'{pnl:+.1f}%' if pnl is not None else '未知'
        pnl_usd = rv.get('sell_pnl_usd') or 0
        lines.append(f"| 盈亏 | {pnl_str} (${pnl_usd:.2f}) |")
        lines.append(f"| 涨幅分档 | {rv['gain_tier']} |")
        lines.append(f"| 入场理由 | {rv['buy_reason']} |")
        lines.append(f"| 出场理由 | {rv['sell_reason']} |")
        lines.append(f"| 入场评估 | {rv['entry_assessment']} |")
        lines.append(f"| 出场评估 | {rv['exit_assessment']} |")
        # 综合判断：只按PnL评价
        pnl_val = rv.get('sell_pnl')
        if pnl_val is not None:
            if pnl_val > 0:
                verdict = "✅ 正确"
            elif pnl_val < 0:
                verdict = "❌ 错误"
            else:
                verdict = "➖ 中性"
        else:
            verdict = "➖ 数据不足"
        lines.append(f"| 综合判断 | {verdict} |")
        lines.append("")
    
    # 策略分析
    lines.append("## 💡 策略复盘\n")
    
    # 按分档统计
    tiers = Counter(rv['gain_tier'] for rv in reviews)
    known_tiers = {k: v for k, v in tiers.items() if k != '未知'}
    if known_tiers:
        lines.append(f"**入场分档分布：** {dict(known_tiers)}\n")
    
    # 盈亏分档
    def _pnl_ok(v):
        p = v.get('sell_pnl')
        return p is not None
    win_tiers = Counter(rv['gain_tier'] for rv in reviews if _pnl_ok(rv) and rv['sell_pnl'] > 0)
    loss_tiers = Counter(rv['gain_tier'] for rv in reviews if _pnl_ok(rv) and rv['sell_pnl'] <= 0)
    if known_tiers:
        lines.append(f"**盈利笔的分档：** {dict(win_tiers)}")
        lines.append(f"**亏损笔的分档：** {dict(loss_tiers)}\n")
    
    # 改进方向
    lines.append("**改进方向：**\n")
    tips = generate_trade_tip(reviews)
    for tip in tips:
        lines.append(f"- {tip}\n")
    
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='逐笔交易复盘')
    parser.add_argument('--date', help='指定日期 YYYY-MM-DD')
    parser.add_argument('--range', type=int, default=1, help='最近N天')
    args = parser.parse_args()
    
    if not os.path.exists(TRADES_PATH):
        print(f"❌ 找不到TRADES.md: {TRADES_PATH}")
        sys.exit(1)
    
    with open(TRADES_PATH) as f:
        text = f.read()
    
    # 提取总权益
    total_current, yesterday_close = extract_equity_totals(text)
    
    buys, sells = parse_trades(text)
    
    # 确定日期范围
    if args.date:
        dates = [args.date]
    else:
        today = datetime.now(BJT).strftime('%Y-%m-%d')
        dates = [
            (datetime.now(BJT) - timedelta(days=i)).strftime('%Y-%m-%d')
            for i in range(args.range)
        ]
    
    for date_label in dates:
        # 过滤当天交易
        day_buys = [b for b in buys if b['ts'].startswith(date_label)]
        day_sells = [s for s in sells if s['ts'].startswith(date_label)]
        
        reviews = review_pairs(day_buys, day_sells)
        report = print_review(reviews, date_label, total_current, yesterday_close)
        
        print(report)
        print("=" * 60)
        print()
        
        # 保存到文件
        os.makedirs(REVIEW_DIR, exist_ok=True)
        review_path = os.path.join(REVIEW_DIR, f"{date_label}.md")
        with open(review_path, 'w') as f:
            f.write(report)
        print(f"  已保存: {review_path}")

if __name__ == '__main__':
    main()
