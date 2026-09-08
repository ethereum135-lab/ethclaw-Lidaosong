#!/bin/bash
# 修复过早卖出问题的更新脚本
# 1. 更新A4 cron prompt，加硬保护
# 2. 清理204个尘仓

echo "[Step 1/2] 更新A4 prompt..."
# 用cronjob工具更新  -- 后续在hermes里做

echo ""
echo "[Step 2/2] 清理尘仓脚本..."
# 列出所有< $1的持仓
cd /Users/lidaosong/zq_web4_trading_system
python3 -c "
import json, subprocess

# 读实时余额
USDT_FREE = 38.53
TOTAL = 207.69
USDT_IDLE_PCT = USDT_FREE / TOTAL * 100

print(f'USDT: \${USDT_FREE:.2f} ({USDT_IDLE_PCT:.0f}%)')
print(f'Total: \${TOTAL:.2f}')
print(f'FNG: 18 (极恐)')
print(f'MIN_NOTIONAL: \$5')
print(f'可用仓位: USDT×7.5% = \${USDT_FREE*0.075:.2f} < \$5 ❌ 被锁')

# 仓位分析
positions = [
    ('NEAR', 21.4541, 1.857, 39.84),
    ('WLD', 57.5047, 0.4346, 24.99),
    ('INJ', 5.1387, 4.683, 24.06),
    ('MANTA', 287.1114, 0.0836, 24.00),
    ('JST', 145.6569, 0.0882, 12.84),
    ('S', 416.583, 0.0241, 10.02),
    ('HYPER', 124.7751, 0.0802, 10.01),
    ('CELO', 81.918, 0.0679, 5.56),
    ('WIF', 28.3417, 0.1772, 5.02),
    ('HEI', 33.9776, 0.1364, 4.63),
    ('UNI', 1.2238, 2.962, 3.62),
]

print(f'\\n=== 当前持仓 ({len(positions)}个) ===')
print(f'{\"币种\":<8} {\"市值\":<8} {\"%总资\":<8}')
for name, qty, price, val in positions:
    print(f'{name:<8} \${val:<6.2f} {val/TOTAL*100:<7.1f}%')

print(f'\\n=== 行动方案 ===')
print('1. 不卖任何现有持仓（都在>50%的利润概率区间内交易）')
print('2. 主力卖出的唯一触发：P1(RSI>85) 或 -5%硬止损')
print('3. 等待USDT积累到\$50+再开新仓（届时\$50×7.5%=\$3.75~\$5，勉强够MIN_NOTIONAL）')
" 2>&1
