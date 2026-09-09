# A9 学研官 — 子蓝图

> **所属系统：** Codex（运维层）
> **职责：** 每日Agent排查 + 新工具/新策略研究
> **运行方式：** 每日
> **更新日期：** 2026-09-09

---

## 1. 身份定义

| 属性 | 值 |
|------|-----|
| Agent编号 | A9 |
| 角色名 | 学研官 |
| 身份 | zq-a9-research-agent |
| 权限 | 全网搜索 + 写入研究报告 |
| 禁止 | 下单、修改策略 |
| 学习频率 | 每天 |
| 协同 | 所有Agent |

## 2. 核心组件

| 组件 | 位置 | 频率 | 说明 |
|------|------|------|------|
| 每日排查 | pipeline_orchestrator.py | 每5分钟 | 全Agent状态检查 |
| 周研究 | agents/a9/weekly_research.md | 每周 | 工具/策略研究 |
| 周报配置 | config/weekly_research.md | — | 研究计划 |
| 工具扫描 | tools/patch_scanner.py | 每周 | 全网工具扫描 |
| 看板 | reports/pipeline_dashboard.html | 每5分钟 | 系统状态看板 |

## 3. 每日排查清单

| 检查项 | 工具 | 频率 |
|--------|------|------|
| 管道编排器状态 | pipeline_orchestrator | 每5分钟 |
| 各阶段任务通过率 | pipeline_dashboard | 每5分钟 |
| 心跳检测 | heartbeat_monitor | 每5分钟 |
| 告警通知 | alert_notifier | 实时 |
| 数据新鲜度 | sync_trading_data | 每5分钟 |
| Cron任务总数 | crontab -l | 每日 |
| 内存/磁盘 | system_monitor | 每5分钟 |
| 错误日志 | watchdog | 持续 |

## 4. 数据流

```
所有系统运行数据
    ↓ A9排查
pipeline_orchestrator (5阶段编排)
    ↓ 写入
reports/pipeline_dashboard.html (状态看板)
audit/ (审计记录)
    ↓ 被读取
老李(看板查看) + ZH(决策参考)
```

## 5. 当前状态

| 指标 | 值 |
|------|-----|
| pipeline_orchestrator | ✅ 运行中(每5分钟) |
| pipeline_dashboard | ✅ 生成中(每5分钟) |
| alert_notifier | ✅ 配置(Telegram+去重+限流) |
| task_runner | ✅ 自动重试(3次+指数退避) |
| weekly_research.md | ✅ 存在 |
| Cron总任务 | 69条(无重复) |

## 6. 缺口与改进

| 项目 | 状态 |
|------|------|
| 每日排查报告 | ⚠️ 看板已有，缺每日汇总推送 |
| Ollama本地推理 | ✅ qwen2.5:0.5b 已部署 |
| 研究自动化 | ⚠️ 当前手动为主 |
