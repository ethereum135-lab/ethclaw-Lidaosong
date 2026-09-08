# Web 4.0 Trading System — 目录库

## 📂 顶层结构

```
zq_web4_trading_system/
├── production/        ← 🟢 正式生产系统（当前在跑）
│   ├── engine/        ← 交易引擎核心
│   └── scripts/       ← 生产级脚本
├── config/            ← ⚙️ 系统配置
│   └── data_sources/  ← 数据源配置
├── data/              ← 📊 运行时数据输出
├── audit/             ← 📝 交易审计日志
├── learning/          ← 📚 全网学习区
├── reports/           ← 📋 研究报告
├── logs/              ← 📟 系统日志
├── memories/          ← 🧠 系统记忆
├── backups/           ← 💾 本地备份
├── tools/             ← 🔧 辅助工具（待整理）
├── archive/           ← 📦 历史归档
├── scripts/           ← 🏗️ 构建/部署脚本
│
├── VERSION            ← 版本号
├── CHANGELOG.md       ← 更新日志
└── DIRECTORY.md       ← 本索引文件
```

## 📖 各目录说明

| 目录 | 用途 | 谁维护 |
|------|------|--------|
| `production/` | 🟢 当前在生产运行的一切，别乱动 | ZQ |
| `config/` | 系统配置、API密钥、铁律、策略地图 | ZQ |
| `data/` | 引擎运行产生的数据快照（node_state.json等） | 引擎自动 |
| `audit/` | TRADES.md / NODES.md / ERRORS.md | 引擎自动 |
| `learning/` | 全网学习报告（9大平台） | 情报/量化/技能猎人 |
| `reports/` | 研究报告、平台调研 | 各团队 |
| `logs/` | 系统日志、每日复盘 | 引擎/复盘 |
| `memories/` | 系统记忆、自我反思 | ZQ |
| `backups/` | 本地备份存档（保留3天） | backup_full.sh |
| `tools/` | 辅助脚本、分析工具 | 各团队 |
| `archive/` | 📦 历史版本、试验品，不会丢但别直接跑 | ZQ |
| `scripts/` | 构建/部署/系统维护脚本 | ZQ |

## ⚡ 快速定位

**想知道系统在跑什么？** → 看 `production/engine/`
**想知道最近交易记录？** → 看 `audit/TRADES.md`
**想知道系统当前版本？** → 看 `VERSION`
**想知道最近改了啥？** → 看 `CHANGELOG.md`
**想找学习资料？** → 看 `learning/`
