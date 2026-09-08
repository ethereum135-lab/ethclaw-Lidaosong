# AWS crontab 完整清单 (2026-08-29 从 /var/log/syslog 还原核对)

> ⚠️ 铁律: 禁止 `crontab -l | grep X | sed | crontab -` 管道覆盖!
> 这会把整个 crontab 删成只剩一行。必须先备份 `crontab -l > /tmp/cron_bak_日期`
> 还原对照 /var/log/syslog 的 CRON 记录, 改完必须 `crontab -l` 验证。

## 15 个任务完整清单

### 每5分钟 (4个核心引擎)
```
*/5 * * * * cd /home/ubuntu/zq_web4_trading_system && /usr/bin/python3 tools/trend_bot.py >> logs/trend_bot.log 2>&1   # 2026-08-31: 网格→趋势通道(Donchian 5d + 2%盈利锁定 v3.1), 旧grid_bot归档 archive/grid_bot_v2_20260831.py
*/5 * * * * cd /home/ubuntu/zq_web4_trading_system && /usr/bin/python3 tools/follow_engine.py >> logs/follow_engine.log 2>&1
*/5 * * * * cd /home/ubuntu/zq_web4_trading_system && /usr/bin/python3 tools/radar_v2.py >> logs/radar.log 2>&1
*/5 * * * * cd /home/ubuntu/zq_web4_trading_system && /usr/bin/python3 production/engine/a4_independent.py >> logs/a4_independent.log 2>&1
```

### 数据采集
```
30 * * * * bash /home/ubuntu/zq_web4_trading_system/data_sources/data_cron.sh news
0 * * * *  bash /home/ubuntu/zq_web4_trading_system/data_sources/data_cron.sh coingecko
0 */2 * * * bash /home/ubuntu/zq_web4_trading_system/data_sources/data_cron.sh sentiment
0 6 * * *  bash /home/ubuntu/zq_web4_trading_system/data_sources/data_cron.sh all
```

### 每日报告/复盘
```
0 21 * * * cd /home/ubuntu/zq_web4_trading_system && /usr/bin/python3 tools/daily_pnl_report.py >> logs/daily_pnl_report.log 2>&1
0 22 * * * cd /home/ubuntu/zq_web4_trading_system && /usr/bin/python3 tools/daily_review.py >> logs/daily_review.log 2>&1
0 22 * * * cd /home/ubuntu/zq_web4_trading_system && /usr/bin/python3 tools/risk_report.py >> logs/risk_report.log 2>&1
0 9 * * *  cd /home/ubuntu/zq_web4_trading_system && /usr/bin/python3 tools/daily_learning.py >> logs/daily_learning.log 2>&1
30 23 * * * cd /home/ubuntu/zq_web4_trading_system && /usr/bin/python3 tools/auto_close_loop.py >> logs/auto_close_loop.log 2>&1
```

### 每周/备份
```
0 3 * * 1 cd /home/ubuntu/zq_web4_trading_system && /usr/bin/python3 tools/update_whitelist.py >> logs/update_whitelist.log 2>&1
0 4 * * * /home/ubuntu/zq_web4_trading_system/auto_backup.sh
0 16 * * * /home/ubuntu/zq_web4_trading_system/auto_backup.sh
```

## 验证方法
- 系统日志: `grep CRON /var/log/syslog | grep ubuntu | tail`
- 每个任务执行时间模式: `grep "任务名" /var/log/syslog | grep -oE "T[0-9]{2}:[0-9]{2}"`
- 核对后: 当前 crontab 任务数应为 15 (含注释行共22行)
