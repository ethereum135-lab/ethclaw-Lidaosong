# tools/ 脚本分类清单

> **审计日期：** 2026-09-09
> **总数：** 71个脚本
> **铁律九执行：** 分类后废弃脚本归入 archive/，.bak文件删除

---

## ✅ 活跃脚本（24个）— 当前系统正在使用

### 策略核心（NAVIGATION.md v3.1）
| 脚本 | 说明 | Cron |
|------|------|------|
| trend_bot.py | **唯一策略执行器**（ETH趋势通道v3.1） | 每10分钟 |
| donchian_strategy.py | Donchian通道计算 | 被trend_bot调用 |
| backtest_donchian.py | Donchian策略回测 | 手动 |

### 数据采集（A1）
| 脚本 | 说明 | Cron |
|------|------|------|
| coin_pool_manager.py | 选币池管理 | 每日05:00 |
| coin_pool_incremental_update.py | 选币池增量更新 | 每日05:30 |
| update_whitelist.py | 白名单更新 | 每日 |
| etherscan_watcher.py | 链上监控 | 每小时 |
| patch_pool.py | 币池补丁 | 手动 |

### 信号分析（A3）
| 脚本 | 说明 | Cron |
|------|------|------|
| a3_signal_scanner.py | A3信号扫描 | 每小时 |
| early_signal_detector.py | 早期信号检测 | 手动 |
| rsi_divergence.py | RSI背离分析 | 手动 |
| btc_rsi_strategy.py | BTC RSI策略 | 手动 |
| radar_v2.py | 雷达系统v2 | 定期 |
| eval_radar.py | 雷达评估 | 定期 |
| trend_analysis.py | 趋势分析 | 定期 |

### 报告与复盘（A5）
| 脚本 | 说明 | Cron |
|------|------|------|
| daily_pnl_report.py | 每日PnL报告 | 每日13:00 |
| daily_profit_ledger.py | 每日盈亏账本 | 每日 |
| daily_learning.py | 每日学习 | 每日 |
| daily_review.py | 每日复盘 | 每日 |
| review_backfeed.py | 回顾反馈 | 定期 |
| risk_report.py | 风控报告 | 定期 |

### 基础设施
| 脚本 | 说明 | Cron |
|------|------|------|
| auto_close_loop.py | 自动收盘循环 | 每日23:30 |
| prediction_market.py | 预测市场 | 每日08:00 |
| prediction_ledger.py | 预测账本 | 定期 |
| param_advisor.py | 参数建议 | 手动 |
| patch_scanner.py | 工具扫描 | 每周 |

---

## 🟡 停用但保留（5个）— 策略已切换，脚本保留供回溯

| 脚本 | 原策略 | 停用日期 | 停用原因 |
|------|--------|----------|----------|
| grid_bot.py | 网格策略 | 2026-09-06 | 改为mean_rev_bot |
| mean_rev_bot.py | 均值回归 | 2026-09-09 | 与NAVIGATION.md冲突 |
| swing_engine.py | 摆动引擎 | 2026-09-09 | 与NAVIGATION.md冲突 |
| htx_loop.py | HTX网格循环 | 2026-09-09 | 网格策略已废弃 |
| follow_engine.py | 跟随引擎 | 2026-09-09 | 与NAVIGATION.md冲突 |

---

## 🔴 废弃脚本（42个）— 归入 archive/deprecated/

### 临时调试脚本（下划线开头，13个）
| 脚本 | 说明 |
|------|------|
| _afternoon_check.py | 午盘检查(临时) |
| _aws_exec.py | AWS执行(临时) |
| _buy_re.py | 买入重试(临时) |
| _check_balance_aws.py | 余额检查(临时) |
| _check_momentum_batch.py | 动量批量检查(临时) |
| _check_new_coins.py | 新币检查(临时) |
| _check_remote.py | 远程检查(临时) |
| _check_signal.py | 信号检查v1(临时) |
| _check_signal2.py | 信号检查v2(临时) |
| _check_signal3.py | 信号检查v3(临时) |
| _check_signals.py | 信号检查(临时) |
| _get_prices.py | 获取价格(临时) |
| _sell_dym.py | 卖出DYM(临时) |

### 尘仓处理（6个，铁律五定案：禁止清尘）
| 脚本 | 说明 |
|------|------|
| dust_convert_exec.py | 尘仓转换执行 |
| dust_convert_recon.py | 尘仓转换侦察 |
| dust_convert_run.py | 尘仓转换运行 |
| dust_test_routes.py | 尘仓路由测试 |
| nfp_convert_retry.py | NFP转换重试 |
| sell_dust_aws.py | 尘仓卖出 |

### 旧策略（8个，已被v3.1替代）
| 脚本 | 说明 |
|------|------|
| simple_gainer_strategy.py | 简单涨幅策略 |
| simple_strategy.py | 简单策略 |
| simple_strategy_v1.py | 简单策略v1 |
| simple_strategy_v2.py | 简单策略v2 |
| binance_band.py | 币安布林带 |
| binance_strategy.py | 币安策略 |
| boost_gainers.py | 增强涨幅 |
| buy_syn.py | 同步买入 |

### 已废弃工具（15个）
| 脚本 | 说明 |
|------|------|
| analyze_gainers.py | 涨幅分析(被a3_signal_scanner替代) |
| check_gainers.py | 涨幅检查(被a3_signal_scanner替代) |
| sell_watchdog.py | 卖出看门狗(被kill_switch替代) |
| record_view.py | 记录查看(临时) |
| test_a4_convert_fallback.py | A4转换回退测试 |
| sig_engine.py | 信号引擎(被辩论引擎替代) |
| backtest_accumulation.py | 累积回测 |
| backtest_e3.py | E3回测 |
| htx_recenter.py | HTX重中心化 |

---

## 统计

| 分类 | 数量 | 占比 |
|------|------|------|
| ✅ 活跃 | 24 | 34% |
| 🟡 停用保留 | 5 | 7% |
| 🔴 废弃 | 42 | 59% |
| **合计** | **71** | 100% |
