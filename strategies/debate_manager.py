#!/usr/bin/env python3
"""
ZQ Web 4.0 辩论决策管理器 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

架构（trading agent 启发）:
  侦察兵ZC (看多方) ───┐
                        ├──→ 总指挥ZH (综合决策) → Blade执行
  风控官FK (看空方) ───┘

流程:
  1. ZC收到候选币 → 写看多报告 (为什么该买, 数据支撑)
  2. FK读到ZC的看多报告 → 写看空反驳 (风险在哪, 数据支撑)
  3. ZH读到完整辩论 → 做最终决策 (buy/hold/sell/skip)
  4. 交易执行后 → 反思模块 → 压缩教训 → 存decision_memory.json
  5. 下次ZH决策 → 先读decision_memory.json

文件接口:
  data/debates/current_debate.json   — 当前进行中的辩论
  data/debates/archive/               — 历史辩论归档
  data/decision_memory.json            — 持久教训记忆
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json, os, sys
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBATE_DIR = os.path.join(BASE_DIR, "data", "debates")
ARCHIVE_DIR = os.path.join(DEBATE_DIR, "archive")
MEMORY_PATH = os.path.join(BASE_DIR, "data", "decision_memory.json")

def _init():
    os.makedirs(DEBATE_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
#  第一步: ZC侦察兵 — 写看多报告
# ═══════════════════════════════════════════════════════════════

def zc_bull_report(coin_symbol, candidates_data, market_data):
    """
    ZC侦察兵生成看多报告。
    这是给ZH（总指挥）看的决策依据，不是给引擎的。
    
    参数:
      coin_symbol: 候选币
      candidates_data: 该币的当前数据 (评分/RSI/量比/趋势/估值等)
      market_data: 大盘数据
    
    返回: 看多报告dict
    """
    report = {
        'role': 'ZC',
        'side': 'bull',
        'coin': coin_symbol,
        'timestamp': datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S'),
        'arguments': [],
        'data_points': {},
        'risk_acknowledged': [],
        'summary': ''
    }
    
    score = candidates_data.get('score', 0)
    rsi = candidates_data.get('rsi', 50)
    vol = candidates_data.get('volume_surge', 1.0)
    trend_4h = candidates_data.get('trend_4h', 0)
    trend_1h = candidates_data.get('trend_1h', 0)
    trend_30m = candidates_data.get('trend', 0)
    change_24h = candidates_data.get('change_24h', 0)
    fr = candidates_data.get('funding_rate', 0)
    
    # 看多论点
    args = []
    
    # 1. 多框架趋势
    if trend_4h >= 1 and trend_1h >= 1:
        args.append(f"多框架趋势共振：4h={trend_4h:+d} 1h={trend_1h:+d} 30m={trend_30m:+d} — 大中小周期同步向上")
    elif trend_4h >= 1:
        args.append(f"4h趋势向上({trend_4h:+d})，大方向没问题")
    
    # 2. 量价健康
    if 0.8 <= vol <= 2.0:
        args.append(f"量比{vol:.2f}x — 温和放量（吸筹阶段），不是爆量接盘")
    elif vol > 2.0:
        args.append(f"量比{vol:.2f}x — 放量活跃，需确认是否已过热")
    
    # 3. RSI合理
    if 30 <= rsi <= 60:
        args.append(f"RSI={rsi:.1f} — 合理区间，有上涨空间，未超买")
    elif 60 < rsi <= 70:
        args.append(f"RSI={rsi:.1f} — 偏强但未过热，趋势延续可持有")
    
    # 4. 涨幅空间
    if -5 <= change_24h <= 10:
        args.append(f"24h涨幅{change_24h:+.2f}% — 有空间，不是暴涨末段")
    
    # 5. 评分趋势
    prev_score = candidates_data.get('prev_score', score)
    if score > prev_score:
        args.append(f"评分从{prev_score}→{score}，数据在改善")
    
    # 6. 费率
    if fr >= -0.01:
        args.append(f"费率{fr:.4f}% — 没被重仓做空")
    
    report['arguments'] = args
    report['data_points'] = {
        'score': score,
        'rsi': rsi,
        'volume_surge': vol,
        'trend_4h': trend_4h,
        'trend_1h': trend_1h,
        'trend_30m': trend_30m,
        'change_24h': change_24h,
        'funding_rate': fr,
        'prev_score': prev_score
    }
    
    # ZC主动承认风险（诚信）
    risks = []
    if rsi > 65:
        risks.append("RSI偏强，可能回调")
    if vol > 2.0:
        risks.append("量比已高，可能已错过最佳买点")
    if change_24h > 8:
        risks.append(f"24h已涨{change_24h:+.2f}%，追高风险")
    if trend_1h <= 0:
        risks.append("1h趋势走平，短期动能不足")
    report['risk_acknowledged'] = risks
    
    report['summary'] = f"ZC看多{coin_symbol}：{'、'.join(args[:3])}" if args else f"ZC无明确看多信号"
    
    return report


# ═══════════════════════════════════════════════════════════════
#  第二步: FK风控官 — 写看空反驳
# ═══════════════════════════════════════════════════════════════

def fk_bear_rebuttal(bull_report, coin_data, market_data):
    """
    FK风控官针对ZC的看多报告逐条反驳。
    学trading agent：FK看到ZC的完整论点，逐条回应，不是各说各话。
    
    参数:
      bull_report: ZC的看多报告（完整内容）
      coin_data: 该币的当前数据（独立获取，不依赖ZC的数据）
      market_data: 大盘数据
    
    返回: 看空反驳报告
    """
    report = {
        'role': 'FK',
        'side': 'bear',
        'rebuttal_to': bull_report.get('coin', '?'),
        'timestamp': datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S'),
        'direct_rebuttals': [],
        'additional_risks': [],
        'summary': ''
    }
    
    score = coin_data.get('score', 0)
    rsi = coin_data.get('rsi', 50)
    vol = coin_data.get('volume_surge', 1.0)
    trend_4h = coin_data.get('trend_4h', 0)
    trend_1h = coin_data.get('trend_1h', 0)
    trend_30m = coin_data.get('trend', 0)
    entry_price = coin_data.get('entry_price', 0)
    current_price = coin_data.get('current_price', 0)
    
    # 逐条反驳ZC的论点
    bull_args = bull_report.get('arguments', [])
    rebuttals = []
    
    for arg in bull_args:
        if '多框架趋势共振' in arg:
            if trend_4h < 1:
                rebuttals.append(f"FK反驳「趋势共振」：FK独立查4h趋势={trend_4h}，不是ZC说的上涨。趋势数据不同步")
            elif trend_1h < 1:
                rebuttals.append(f"FK质疑「趋势共振」：4h向上但1h={trend_1h:+d}，30m={trend_30m:+d}，短期在走弱")
        
        if '温和放量' in arg or '吸筹' in arg:
            if trend_30m < 0:
                rebuttals.append(f"FK反驳「温和放量」：量放大但30m趋势={trend_30m:+d}在跌，可能是出货不是吸筹")
        
        if 'RSI' in arg and '合理' in arg and rsi > 60:
            rebuttals.append(f"FK质疑RSI：RSI={rsi:.1f}已偏高，ZC说是合理区间，但历史上RSI>60后继续上涨的概率在下降")
        
        if '有空间' in arg:
            if entry_price > 0 and current_price > 0:
                change = (current_price - entry_price) / entry_price * 100
                if change > 5:
                    rebuttals.append(f"FK提醒：从入场已涨{change:+.1f}%，空间在收窄，不是ZC说的'还有空间'")
    
    # FK独立发现的风险
    additional = []
    
    # 大盘风控
    md = market_data.get('direction', 'neutral')
    if md in ('mild_bear', 'bearish'):
        additional.append(f"大盘{md}(总得分{market_data.get('overall_score', 0)})，逆势做多胜率低")
    
    # 历史教训
    memory = load_memory()
    recent_lessons = [m for m in memory if m.get('effect', 0) >= 1][-3:]
    for lesson in recent_lessons:
        additional.append(f"历史教训#{lesson['id']}：{lesson['lesson'][:60]}")
    
    report['direct_rebuttals'] = rebuttals
    report['additional_risks'] = additional
    report['summary'] = f"FK看空{coin_data.get('symbol','?')}：{'、'.join(rebuttals[:2])}" if rebuttals else f"FK无明确反驳"
    
    return report


# ═══════════════════════════════════════════════════════════════
#  第三步: ZH总指挥 — 综合决策
# ═══════════════════════════════════════════════════════════════

def zh_decision(bull_report, bear_rebuttal, market_data, position_data):
    """
    ZH总指挥拿到ZC看多 + FK看空两份完整报告后做决策。
    不是"哪边论点多选哪边"，而是综合评估后做判断。
    
    返回: {
      'decision': 'buy'/'hold'/'sell'/'skip',
      'reason': 决策理由,
      'conviction': 'high'/'medium'/'low'
    }
    """
    coin = bull_report.get('coin', '?')
    bull_summary = bull_report.get('summary', '')
    bear_summary = bear_rebuttal.get('summary', '')
    
    bull_args = bull_report.get('arguments', [])
    bear_rebuttals = bear_rebuttal.get('direct_rebuttals', [])
    bear_risks = bear_rebuttal.get('additional_risks', [])
    
    market_dir = market_data.get('direction', 'neutral')
    current_holdings = position_data.get('current_holdings', {})
    usdt_available = position_data.get('usdt_available', 0)
    
    # 权重评分
    bull_weight = len(bull_args) * 2  # 每个看多论点2分
    bear_weight = len(bear_rebuttals) * 3 + len(bear_risks) * 2  # 反驳权重更高
    
    # 市场方向权重
    if market_dir in ('bearish', 'mild_bear'):
        bear_weight += 5
    elif market_dir == 'bullish':
        bull_weight += 5
    
    # 是否有持仓（已有持仓→倾向于持有）
    is_holding = coin in current_holdings
    if is_holding:
        bull_weight += 3  # 持仓倾向持有
    
    # 决策
    net = bull_weight - bear_weight
    
    decision = 'skip'
    conviction = 'low'
    reason_parts = []
    
    if net >= 5:
        decision = 'buy'
        conviction = 'high' if net >= 10 else 'medium'
        reason_parts.append(f"看多权重{bull_weight} > 看空权重{bear_weight}（+{net}）")
    elif net >= 0:
        decision = 'hold' if is_holding else 'skip'
        conviction = 'medium' if is_holding else 'low'
        reason_parts.append(f"势均力敌({bull_weight}/{bear_weight})，{'持仓不动' if is_holding else '不入场'}")
    else:
        if is_holding:
            decision = 'sell'
            conviction = 'medium'
            reason_parts.append(f"看空权重{bear_weight} > 看多权重{bull_weight}（-{abs(net)}），离场观望")
        else:
            decision = 'skip'
            conviction = 'high' if net <= -5 else 'medium'
            reason_parts.append(f"看空占优({bear_weight}/{bull_weight})，不入场等待")
    
    # 附加理由
    if bear_rebuttals:
        reason_parts.append(f"FK反驳要点: {bear_rebuttals[0]}")
    if bear_risks:
        reason_parts.append(f"风险: {bear_risks[0][:40]}")
    if market_dir != 'neutral':
        reason_parts.append(f"大盘{market_dir}")
    
    return {
        'coin': coin,
        'decision': decision,
        'conviction': conviction,
        'reason': '｜'.join(reason_parts),
        'bull_weight': bull_weight,
        'bear_weight': bear_weight,
        'net_score': net,
        'timestamp': datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')
    }


# ═══════════════════════════════════════════════════════════════
#  第四步: 反思模块 — 压缩教训
# ═══════════════════════════════════════════════════════════════

def reflect(outcome_data):
    """
    交易执行后，反思决策过程，压缩成2-4句话的教训。
    写入decision_memory.json，供下次决策使用。
    
    outcome_data: {
      'coin': 'BTC',
      'entry_price': 85000,
      'exit_price': 86000,
      'hold_minutes': 120,
      'pnl_pct': 1.18,
      'decision_was': 'buy',
      'bull_args': [...],
      'bear_args': [...],
      'what_worked': '趋势共振判断准确',
      'what_failed': '出场太早，4h趋势还在'
    }
    """
    memory = load_memory()
    next_id = max([m['id'] for m in memory], default=0) + 1
    
    coin = outcome_data.get('coin', '?')
    pnl = outcome_data.get('pnl_pct', 0)
    hold_mins = outcome_data.get('hold_minutes', 0)
    what_worked = outcome_data.get('what_worked', '')
    what_failed = outcome_data.get('what_failed', '')
    bull_args = outcome_data.get('bull_args', [])
    bear_args = outcome_data.get('bear_args', [])
    
    # 压缩成2-4句话
    parts = []
    
    # 第1句：结果
    if pnl > 0:
        parts.append(f"{coin}持{hold_mins}分赚{pnl:+.2f}%")
    else:
        parts.append(f"{coin}持{hold_mins}分亏{pnl:.2f}%")
    
    # 第2句：什么对了
    if what_worked:
        parts.append(f"对:{what_worked}")
    
    # 第3句：什么错了
    if what_failed:
        parts.append(f"错:{what_failed}")
    
    # 第4句：下次怎么做（可复现的信号）
    if pnl > 0:
        # 赚钱的交易提取可复现信号
        if bull_args:
            parts.append(f"信号:{bull_args[0][:40]}")
    else:
        # 亏钱的交易提取要避免的
        if bear_args:
            parts.append(f"教训:{bear_args[0][:40]}")
    
    lesson = '|'.join(parts)
    
    entry = {
        'id': next_id,
        'lesson': lesson,
        'date': datetime.now(BJT).strftime('%Y-%m-%d'),
        'coin': coin,
        'pnl_pct': round(pnl, 2),
        'hold_minutes': hold_mins,
        'category': 'win' if pnl > 0 else 'loss',
        'effect': 0  # 0=未验证, 1=已验证有用
    }
    
    memory.append(entry)
    
    # 最多保留50条
    if len(memory) > 50:
        memory = memory[-50:]
    
    save_memory(memory)
    print(f"  📝 决策记忆#{next_id}: {lesson[:80]}...")
    
    return entry


# ═══════════════════════════════════════════════════════════════
#  第2.5步：ZC回应FK反驳（TradingAgents多轮辩论机制）
# ═══════════════════════════════════════════════════════════════

def zc_rejoinder(bull_report, bear_rebuttal, coin_data):
    """
    ZC看到FK的逐条反驳后，再次论证。
    学TradingAgents：bull看到bear的论点后直接反驳，不是各说各话。
    
    参数:
      bull_report: ZC自己的看多报告
      bear_rebuttal: FK的逐条反驳
      coin_data: 当前数据
    
    返回: {
      'responses': [对每条反驳的回应],
      'conceded_points': [ZC承认FK说得对的地方],
      'updated_conviction': 'strengthened'/'unchanged'/'weakened'
    }
    """
    score = coin_data.get('score', 0)
    rsi = coin_data.get('rsi', 50)
    trend_4h = coin_data.get('trend_4h', 0)
    
    responses = []
    conceded = []
    
    for rebuttal in bear_rebuttal.get('direct_rebuttals', []):
        if 'FK反驳' in rebuttal or 'FK质疑' in rebuttal or 'FK提醒' in rebuttal:
            # 检查数据是否真的支持FK的反驳
            if '趋势共振' in rebuttal and trend_4h >= 1:
                responses.append(f"FK说趋势不共振，但4h趋势={trend_4h:+d}仍向上，大方向没变。1h短期波动不影响中期判断")
            elif 'RSI' in rebuttal and rsi < 65:
                responses.append(f"FK说RSI偏高，但RSI={rsi:.1f}未超买，仍在合理范围")
            elif '出货' in rebuttal:
                responses.append(f"FK说可能是出货，但评分{score}在改善，暂不支持出货判断")
            else:
                # 数据确实支持FK → ZC承认
                conceded.append(rebuttal[:50])
    
    # 如果ZC承认了太多点 → 信心降低
    conviction = 'weakened' if len(conceded) >= 2 else 'unchanged'
    if len(responses) >= 2 and len(conceded) <= 1:
        conviction = 'strengthened'
    
    return {
        'responses': responses if responses else ['ZC：FK的反驳基于短期数据，不改变中期看多判断'],
        'conceded_points': conceded,
        'updated_conviction': conviction
    }


# ═══════════════════════════════════════════════════════════════
#  第2.75步：FK三视角风控分析（TradingAgents风控辩论机制）
# ═══════════════════════════════════════════════════════════════

def fk_three_perspectives(bull_report, bear_rebuttal, rejoinder, coin_data, market_data):
    """
    FK从三个视角分析同一笔交易。
    学TradingAgents的aggressive/conservative/neutral三风格风控辩论。
    
    参数:
      bull_report: ZC看多报告
      bear_rebuttal: FK第一轮反驳
      rejoinder: ZC的回应
      coin_data: 当前数据
      market_data: 大盘数据
    
    返回: {
      'aggressive': {分析, tags, summary},
      'conservative': {分析, tags, summary},
      'neutral': {分析, tags, summary}
    }
    """
    score = coin_data.get('score', 0)
    rsi = coin_data.get('rsi', 50)
    vol = coin_data.get('volume_surge', 1.0)
    trend_4h = coin_data.get('trend_4h', 0)
    market_dir = market_data.get('direction', 'neutral')
    
    # 激进派(aggressive)：看到机会，看多逻辑成立就敢进
    aggressive = {
        'analysis': '',
        'tags': [],
        'summary': '',
        'verdict': 'approve'
    }
    agg_reasons = []
    if score >= 60:
        agg_reasons.append(f"评分{score}够高")
    if trend_4h >= 1:
        agg_reasons.append(f"4h趋势{trend_4h:+d}向上")
    if vol >= 0.8:
        agg_reasons.append(f"量比{vol:.1f}x有量")
    if market_dir in ('bullish', 'mild_bull', 'neutral'):
        agg_reasons.append(f"大盘{market_dir}允许进场")
    
    if len(agg_reasons) >= 2:
        aggressive['tags'] = ['机会明确', '有数据支撑'] + agg_reasons[:2]
        aggressive['summary'] = f"激进派：可以进场。{'、'.join(agg_reasons[:3])}"
        aggressive['verdict'] = 'approve'
    else:
        aggressive['tags'] = ['数据不足']
        aggressive['summary'] = f"激进派：数据不够强。仅{len(agg_reasons)}个看多信号"
        aggressive['verdict'] = 'hold'
    
    # 保守派(conservative)：看到风险，保护资产优先
    conservative = {
        'analysis': '',
        'tags': [],
        'summary': '',
        'verdict': 'reject'
    }
    con_reasons = []
    bear_rebuttals = bear_rebuttal.get('direct_rebuttals', [])
    if len(bear_rebuttals) >= 2:
        con_reasons.append(f"FK有{len(bear_rebuttals)}条反驳")
    if rsi > 65:
        con_reasons.append(f"RSI={rsi:.1f}偏高")
    if rejoinder.get('updated_conviction') == 'weakened':
        con_reasons.append("ZC自己也承认了部分风险")
    if market_dir in ('bearish', 'mild_bear'):
        con_reasons.append(f"大盘{market_dir}")
    
    if len(con_reasons) >= 2:
        conservative['tags'] = ['风险偏高', '不宜追高'] + con_reasons[:2]
        conservative['summary'] = f"保守派：不进场。{'、'.join(con_reasons[:3])}"
        conservative['verdict'] = 'reject'
    else:
        conservative['tags'] = ['风险可控']
        conservative['summary'] = "保守派：风险可控，可以谨慎参与"
        conservative['verdict'] = 'approve'
    
    # 中性派(neutral)：平衡视角，看综合得分
    neutral = {
        'analysis': '',
        'tags': [],
        'summary': '',
        'verdict': 'hold'
    }
    
    # 综合得分
    net = 0
    if score >= 60: net += 2
    if trend_4h >= 1: net += 2
    if 30 <= rsi <= 60: net += 1
    if 0.8 <= vol <= 1.5: net += 1
    if len(bear_rebuttals) >= 2: net -= 2
    if market_dir in ('bearish', 'mild_bear'): net -= 1
    
    if net >= 3:
        neutral['tags'] = ['中性偏多', f'综合分+{net}']
        neutral['summary'] = f"中性派：偏多。综合分+{net}，支持进场"
        neutral['verdict'] = 'approve'
    elif net >= 0:
        neutral['tags'] = ['中性', f'综合分+{net}']
        neutral['summary'] = f"中性派：观望。综合分+{net}，等更明确信号"
        neutral['verdict'] = 'hold'
    else:
        neutral['tags'] = ['中性偏空', f'综合分{net}']
        neutral['summary'] = f"中性派：偏空。综合分{net}，不建议进场"
        neutral['verdict'] = 'reject'
    
    return {
        'aggressive': aggressive,
        'conservative': conservative,
        'neutral': neutral
    }


# ═══════════════════════════════════════════════════════════════
#  ZH决策 v2：综合Bull/Bear/Rejoinder/三风控
# ═══════════════════════════════════════════════════════════════

def zh_decision_v2(bull_report, bear_rebuttal, rejoinder, three_views, market_data, position_data):
    """
    ZH拿到所有输入后做最终决策：
    - ZC看多（第1轮）
    - FK看空反驳（第1轮）
    - ZC回应（第2轮）
    - FK三视角风控（激进/保守/中性）
    - 大盘方向
    - 当前持仓
    
    学TradingAgents：Portfolio Manager综合所有分析做最终批准/拒绝。
    """
    coin = bull_report.get('coin', '?')
    current_holdings = position_data.get('current_holdings', {})
    is_holding = coin in current_holdings
    
    # 统计风控三视角的投票
    verdicts = [v['verdict'] for v in three_views.values()]
    approve_count = verdicts.count('approve')
    reject_count = verdicts.count('reject')
    hold_count = verdicts.count('hold')
    
    # ZC信心
    conviction = rejoinder.get('updated_conviction', 'unchanged')
    zc_weakened = conviction == 'weakened'
    
    # 决策逻辑
    decision = 'skip'
    confidence = 'low'
    reasons = []
    
    if approve_count >= 2 and not zc_weakened:
        # 三风控多数同意 + ZC没认输
        decision = 'buy'
        confidence = 'high' if approve_count == 3 else 'medium'
        agg_v = three_views["aggressive"]["verdict"][0].upper()
        con_v = three_views["conservative"]["verdict"][0].upper()
        neu_v = three_views["neutral"]["verdict"][0].upper()
        reasons.append(f"三风控{approve_count}/{len(verdicts)}同意（激{agg_v}保{con_v}中{neu_v}）")
        reasons.append(f"ZC看多+FK反驳后ZC{(conviction)}")
    elif reject_count >= 2:
        # 三风控多数反对
        if is_holding:
            decision = 'sell'
            confidence = 'medium'
            reasons.append(f"三风控{reject_count}/{len(verdicts)}反对，持仓离场")
        else:
            decision = 'skip'
            confidence = 'high' if reject_count == 3 else 'medium'
            reasons.append(f"三风控{reject_count}/{len(verdicts)}反对，不入场")
    else:
        # 2:1或势均力敌
        if is_holding:
            decision = 'hold'
            confidence = 'medium'
            reasons.append(f"风控分票({approve_count}同意/{reject_count}反对/{hold_count}中立)，持仓不动")
        else:
            decision = 'skip'
            confidence = 'low'
            reasons.append(f"风控分票，等更明确信号")
    
    return {
        'coin': coin,
        'decision': decision,
        'conviction': confidence,
        'reason': '｜'.join(reasons),
        'fk_verdicts': verdicts,
        'timestamp': datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')
    }


# ═══════════════════════════════════════════════════════════════
#  完整辩论流程 v2 — TradingAgents多轮辩论 + 三视角风控
# ═══════════════════════════════════════════════════════════════

def run_full_debate(coin_symbol, coin_data, market_data, position_data):
    """
    跑完整的多轮辩论→三风控视角→ZH决策→反思流程。
    
    流程（学TradingAgents）：
      第1轮：ZC写看多 → FK逐条反驳
      第2轮：ZC看到FK的反驳 → ZC再次论证（回应反驳）
      FK三视角各自分析：激进派(敢进) / 保守派(保本) / 中性派(平衡)
      ZH综合所有视角做决策
      反思模块压缩教训存decision_memory.json
    
    返回: {
      'debate_id': str,
      'bull_report': dict,
      'bear_rebuttal': dict,
      'bull_rejoinder': dict,  ← 新增：ZC对FK反驳的回应
      'fk_three_views': dict,  ← 新增：三风控视角
      'zh_decision': dict,
      'file_path': str
    }
    """
    _init()
    
    coin = coin_symbol
    
    # ── 第1轮：ZC看多 → FK反驳 ──
    print(f"\n  {'='*50}")
    print(f"  📗 第1轮：ZC看多 — {coin}")
    print(f"  {'='*50}")
    bull = zc_bull_report(coin, coin_data, market_data)
    for a in bull['arguments']:
        print(f"    ✅ {a}")
    if bull['risk_acknowledged']:
        print(f"    ⚠️ ZC自认风险: {'; '.join(bull['risk_acknowledged'])}")
    
    print(f"\n  {'='*50}")
    print(f"  📕 FK逐条反驳 — {coin}")
    print(f"  {'='*50}")
    bear = fk_bear_rebuttal(bull, coin_data, market_data)
    for r in bear['direct_rebuttals']:
        print(f"    🔴 {r}")
    for r in bear['additional_risks']:
        print(f"    ⚠️ {r}")
    
    # ── 第2轮：ZC看到FK的反驳 → ZC回应 ──
    print(f"\n  {'='*50}")
    print(f"  📗 第2轮：ZC回应FK反驳 — {coin}")
    print(f"  {'='*50}")
    rejoinder = zc_rejoinder(bull, bear, coin_data)
    for a in rejoinder['responses']:
        print(f"    🔵 {a}")
    if rejoinder['conceded_points']:
        print(f"    🤝 ZC承认的点: {'; '.join(rejoinder['conceded_points'])}")
    
    # ── FK三视角风控分析 ──
    print(f"\n  {'='*50}")
    print(f"  🔍 FK三视角风控 — {coin}")
    print(f"  {'='*50}")
    three_views = fk_three_perspectives(bull, bear, rejoinder, coin_data, market_data)
    for view_name, view in three_views.items():
        emoji = {'aggressive': '🔥', 'conservative': '🛡️', 'neutral': '⚖️'}.get(view_name, '📋')
        print(f"  {emoji} {view_name.upper()}: {view['summary'][:80]}")
        for tag in view.get('tags', []):
            print(f"       #{tag}")
    
    # ── ZH综合决策 ──
    print(f"\n  {'='*50}")
    print(f"  🎯 ZH综合决策")
    print(f"  {'='*50}")
    decision = zh_decision_v2(bull, bear, rejoinder, three_views, market_data, position_data)
    emoji = '🟢' if decision['decision'] == 'buy' else ('🟡' if decision['decision'] == 'hold' else ('🔴' if decision['decision'] == 'sell' else '⚪'))
    print(f"  {emoji} 决策: {decision['decision'].upper()} (信心:{decision['conviction']})")
    print(f"  理由: {decision['reason']}")
    
    # 保存辩论记录
    debate_id = datetime.now(BJT).strftime('%Y%m%d_%H%M')
    debate_record = {
        'debate_id': debate_id,
        'coin': coin,
        'timestamp': datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S'),
        'bull_report': bull,
        'bear_rebuttal': bear,
        'bull_rejoinder': rejoinder,
        'fk_three_views': three_views,
        'zh_decision': decision
    }
    
    file_path = os.path.join(DEBATE_DIR, f"{debate_id}_{coin}.json")
    with open(file_path, 'w') as f:
        json.dump(debate_record, f, indent=2, ensure_ascii=False)
    print(f"  💾 辩论已保存: {file_path}")
    
    return {
        'debate_id': debate_id,
        'bull_report': bull,
        'bear_rebuttal': bear,
        'bull_rejoinder': rejoinder,
        'fk_three_views': three_views,
        'zh_decision': decision,
        'file_path': file_path
    }


# ═══════════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════════

def load_memory():
    """读取决策记忆"""
    if not os.path.exists(MEMORY_PATH):
        return []
    with open(MEMORY_PATH) as f:
        return json.load(f)

def save_memory(memory):
    """保存决策记忆"""
    with open(MEMORY_PATH, 'w') as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

def get_recent_lessons(limit=3):
    """获取最近的决策教训（供ZH决策前阅读）"""
    memory = load_memory()
    # 先取已验证有用的，再取最近的
    validated = [m for m in memory if m.get('effect', 0) >= 1][-limit:]
    recent = [m for m in memory if m.get('effect', 0) < 1][-limit:]
    return validated + recent


# ═══════════════════════════════════════════════════════════════
#  独立测试
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════╗
    ║   ZQ 辩论决策管理器 — 测试模式               ║
    ╚══════════════════════════════════════════════╝
    """)
    
    # 模拟数据测试
    test_coin = 'BTCUSDT'
    test_data = {
        'score': 88.6, 'rsi': 52.3, 'volume_surge': 1.16,
        'trend_4h': 1, 'trend_1h': 1, 'trend': 1,
        'change_24h': 3.45, 'funding_rate': 0.005,
        'prev_score': 82.0,
        'symbol': test_coin
    }
    test_market = {
        'direction': 'neutral', 'overall_score': 0
    }
    test_position = {
        'usdt_available': 394.48,
        'current_holdings': {}
    }
    
    result = run_full_debate(test_coin, test_data, test_market, test_position)
    print(f"\n✅ 辩论完成 → {result['zh_decision']['decision']}")
    
    # 测试反思
    test_outcome = {
        'coin': test_coin,
        'entry_price': 85000, 'exit_price': 86000,
        'hold_minutes': 120, 'pnl_pct': 1.18,
        'decision_was': 'buy',
        'bull_args': ['多框架趋势共振：4h=+1 1h=+1 — 大中小周期向上'],
        'bear_args': ['FK反驳「趋势共振」：30m={trend_30m:+d}短期走弱'],
        'what_worked': '4h趋势判断准确',
        'what_failed': '出场略早，1h趋势还在'
    }
    reflect(test_outcome)
    print(f"\n当前决策记忆: {len(load_memory())}条")
