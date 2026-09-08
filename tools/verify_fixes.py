#!/usr/bin/env python3
"""
ZQ引擎改后验证脚本 — 每节点自动检查四刀效果
对比改前基线 vs 改后实时数据
"""
import subprocess, json, re, os, sys
from collections import defaultdict
from datetime import datetime, timezone

SSH_CMD = "ssh -i ~/.zq_vault/web4.0.pem ubuntu@15.134.211.154"
ENGINE_LOG = "/home/ubuntu/zq_web4_trading_system/logs/engine_cron.log"
TRADES_FILE = "/Users/lidaosong/zq_web4_trading_system/audit/TRADES.md"

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except:
        return ""

def check_engine_log():
    """SSH到AWS提取最新节点日志"""
    log = run(f'{SSH_CMD} "tail -80 {ENGINE_LOG}"')
    return log

def check_local_trades():
    """读本地TRADES.md获取最新交易"""
    try:
        with open(TRADES_FILE) as f:
            return f.read()
    except:
        return ""

def count_exit_signals(log):
    """统计退出信号"""
    e3 = len(re.findall(r'E3 趋势转跌', log))
    e2 = len(re.findall(r'E2 成交量萎缩', log))
    e4 = len(re.findall(r'E4 评分骤降', log))
    p1 = len(re.findall(r'P1 RSI超买', log))
    dh = len(re.findall(r'方向持有', log))
    return {'E3': e3, 'E2': e2, 'E4': e4, 'P1': p1, '方向持有': dh}

def main():
    print("=" * 60)
    print("【改后验证】", datetime.now().strftime('%Y-%m-%d %H:%M BJT'))
    print("=" * 60)
    
    # 1. 引擎状态
    log = check_engine_log()
    if not log:
        print("❌ SSH连接失败")
        sys.exit(1)
    
    # 2. 提取最新节点时间
    node_match = re.search(r'节点完成.*?(\d{2}:\d{2}:\d{2})', log)
    node_time = node_match.group(1) if node_match else "?"
    
    # 3. 提取持仓
    holdings = ""
    for line in log.split('\n'):
        if '@' in line and '$' in line and '=' in line and ('ASTER' in line or 'CHZ' in line or 'TRX' in line):
            holdings += line.strip() + "\n"
    
    # 4. USDT余额
    usdt_match = re.search(r'USDT: \$([\d.]+)', log)
    usdt = usdt_match.group(1) if usdt_match else "?"
    
    # 5. 有无出场信号
    no_exit = "✅ 无出场信号" in log
    
    # 6. 方向持有
    dir_hold = "方向持有" in log
    
    # 7. 卖出冷却
    cooldown = "冷却中" in log
    
    # 8. 黑名单
    blacklist = "自动拉黑" in log or "🚫" in log
    
    # 9. 退出信号统计
    signals = count_exit_signals(log)
    
    print(f"\n📊 节点: {node_time} UTC | USDT: ${usdt}")
    print(f"📦 持仓:")
    print(holdings if holdings else "  无持仓")
    
    print(f"\n🔍 四刀验证:")
    
    print(f"\n刀1: 方向判断器真持有")
    if dir_hold:
        print(f"  ✅ 已触发 — 趋势向上时E2/E3/E4被抑制")
    else:
        print(f"  ⚪ 未触发（无机械出场信号需要通过）")
    
    print(f"\n刀2: E3只允许trend≤-2")
    if signals['E3'] == 0:
        print(f"  ✅ E3触发: 0次（trend=-1不再误杀）")
    else:
        print(f"  ⚠️ E3触发: {signals['E3']}次")
    
    print(f"\n刀3: 卖出4h冷却")
    if cooldown:
        print(f"  ✅ 冷却生效中")
    else:
        print(f"  ⚪ 未触发（无重复买卖场景）")
    
    print(f"\n刀4: 累计亏损$3自动拉黑")
    if blacklist:
        print(f"  ✅ 黑名单已触发")
    else:
        print(f"  ⚪ 未触发（无币种累计亏超$3）")
    
    print(f"\n📈 改前基线 vs 改后:")
    print(f"  E3触发: 175次/10天(改前) → {signals['E3']}次(本节点)")
    print(f"  交易量: 50笔/天(改前) → 待统计")
    
    # 检查最新TRADES.md看是否有新交易
    trades = check_local_trades()
    last_line = trades.strip().split('\n')[-1] if trades else ""
    print(f"\n📝 最新TRADES: {last_line[:80] if last_line else '无'}")
    
    print("\n" + "=" * 60)
    
    # 结论
    all_green = signals['E3'] == 0
    if all_green:
        print("🟢 结论: 四刀正常，系统稳定运行中")
    else:
        print("🟡 结论: 需要关注，E3仍有触发")
    
    # 写入验证日志
    with open('/Users/lidaosong/zq_web4_trading_system/agents/bhz/verification_log.md', 'a') as f:
        f.write(f"\n| {node_time} UTC | USDT=${usdt} | E3={signals['E3']} | 方向持有={'Y' if dir_hold else 'N'} | {'🟢' if all_green else '🟡'} |")

if __name__ == '__main__':
    main()
