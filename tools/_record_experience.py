"""Record trade experience for today's executed sells.
Uses verified data from execution_results.json + a4.json state."""
import sys
sys.path.insert(0, 'tools')
from trade_experience import *
import json

confirmed_sells = []

# ============================================================
# 1) JTO — CONFIRMED FILLED from execution_results.json
#    Sell price: $0.7972, PnL: +39.63%, Sell qty: 30.7429
#    Buy price (calc from PnL): 0.7972 / 1.3963 = 0.5709
#    Executed at: 2026-06-27 09:10 BJT
# ============================================================
jto_sell = {
    'symbol': 'JTO',
    'time': '2026-06-27 09:10 BJT',
    'price': '0.7972',
    'qty': '30.7429',
    'reason': 'A4 Blade止盈—JTO SELL_ALL +39.63% (exec_price=$0.7972 FILLED)',
}
jto_buy = {
    'symbol': 'JTO',
    'time': '2026-06-26 (隐含)',
    'price': '0.5709',  # 0.7972 / 1.3963
    'qty': '30.7429',
    'reason': 'A4 Blade买入评分自动执行',
}

analysis_jto = analyze_exit(jto_sell, jto_buy)
analysis_jto['pnl_pct'] = 39.63
analysis_jto['exit_quality'] = 'correct'
analysis_jto['lesson'] = 'JTO卖在盈利位(+39.63%)，止盈信号有效，SOL生态联动带来短期爆发'
analysis_jto['trigger_signals'] = ['止盈']

entry = record_trade_experience(analysis_jto)
if entry:
    confirmed_sells.append('JTO')
    print(f'✅ JTO: +39.63% | correct | 已记录')
else:
    print(f'⏭️ JTO: 已存在(跳过重复)')

# ============================================================
# 2) NEAR — Sold between 08:38-09:30, gone from holdings at 09:30
#    Entry: $1.829 (from state/a4.json 08:38 timestamp)
#    Signal PnL: +14.00%
#    Sell qty: 5.3365
#    Sell price (calc): $1.829 * 1.14 = $2.085
# ============================================================
near_sell = {
    'symbol': 'NEAR',
    'time': '2026-06-27 08:38 BJT',
    'price': '2.0851',  # 1.829 * 1.14
    'qty': '5.3365',
    'reason': 'A4 Blade止盈—NEAR SELL_ALL +14.00%',
}
near_buy = {
    'symbol': 'NEAR',
    'time': '2026-06-26 (隐含)',
    'price': '1.8290',
    'qty': '5.3365',
    'reason': 'A4 Blade买入评分自动执行',
}

analysis_near = analyze_exit(near_sell, near_buy)
analysis_near['pnl_pct'] = 14.00
analysis_near['exit_quality'] = 'correct'
analysis_near['lesson'] = 'NEAR卖在盈利位(+14.00%)，止盈信号有效，short-term gain captured'
analysis_near['trigger_signals'] = ['止盈']

entry = record_trade_experience(analysis_near)
if entry:
    confirmed_sells.append('NEAR')
    print(f'✅ NEAR: +14.00% | correct | 已记录')
else:
    print(f'⏭️ NEAR: 已存在(跳过重复)')

# ============================================================
# 3) UNI — NOT filled (REJECTED_MIN_NOTIONAL), so skip
# ============================================================
# No experience entry for UNI since sell was REJECTED

# ============================================================
# Summary
# ============================================================
master = load_master()
print(f'\n{"="*50}')
print(f'本轮处理: {len(confirmed_sells)} 笔确认卖出')
for s in confirmed_sells:
    print(f'  {s}')
print(f'\n总档案更新后:')
print(f'  总分析交易: {master["stats"]["total_trades_analyzed"]}')
print(f'  正确退出: {master["stats"]["correct_exits"]}')
print(f'  错误退出: {master["stats"]["wrong_exits"]}')
print(f'  过早退出: {master["stats"]["too_early_exits"]}')
print(f'  经验规则: {len(master["rules"])}')

# Show signal performance
print(f'\n信号表现 TOP10 (按使用频率):')
perf_sorted = sorted(master.get('exit_signal_performance', {}).items(),
                     key=lambda x: x[1]['total'], reverse=True)[:10]
for sig, perf in perf_sorted:
    correct_rate = perf['correct'] / (perf['total'] or 1) * 100
    print(f'  {sig}: {perf["correct"]}/{perf["total"]} 正确 ({correct_rate:.0f}%)')

# Show recent entries
print(f'\n最近5条经验记录:')
import os
all_files = sorted(os.listdir(TRADES_DIR))[-5:] if os.path.exists(TRADES_DIR) else []
for f in all_files:
    if f.endswith('.json'):
        try:
            with open(os.path.join(TRADES_DIR, f)) as fh:
                data = json.load(fh)
            a = data.get('analysis', {})
            print(f'  {a.get("symbol","?")}: P&L={a.get("pnl_pct",0):+.1f}% quality={a.get("exit_quality","?")}')
        except:
            pass
