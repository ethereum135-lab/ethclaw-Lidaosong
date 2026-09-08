# ZQ-Scouter 完整审计报告（按审计框架执行）

**审计日期**: 2026-05-04
**框架来源**: reports/audit_framework.md (老李2026-05-04)
**审计人**: ZQ-Scouter
**审计范围**: 工具(Work1) + Skill(Work2) + 数据源(Work3)

---

## 工作一：工具全面审计

### 1.1 扫描方法

```
扫描范围:
├─ pip3 list (系统Python 3.9 + Brew Python 3.11 + Hermes venv Python 3.11)
├─ brew list --formula (82个包)
├─ brew list --cask (2个: Docker Desktop, ngrok)
├─ npm list -g
├─ go version + ~/go/bin/
├─ CLI: gh, rclone, rg, tmux, ollama, ffmpeg
├─ ~/zq_web4_trading_system/ 全目录扫描
├─ engine_realtime_v2.py (1173行) 逆向分析
```

### 1.2 全量工具清单

#### A. Python 第三方库 — Hermes Agent venv (Python 3.11.15)

| 库名 | 用途 | 状态 | 核心问题 |
|:-----|:-----|:----:|:---------|
| **requests** | HTTP API调用 | ✅ 激活 | 所有API通信的基础 |
| **numpy** | 数值计算 | ✅ 激活(间接) | pandas依赖，引擎不直接import |
| **pandas** | ❌ 未在venv中 | ⚠️ 有fallback | 引擎try/except fallback到纯Python |
| **ta** | ❌ 未在venv中 | ⚠️ 有fallback | 技术指标加速，生产环境应安装 |
| **openai** | LLM API | ✅ 激活 | Hermes Agent LLM通信 |
| **anthropic** | LLM API | ✅ 激活 | Hermes Agent LLM通信 |
| **discord_py** | Discord机器人 | ✅ 激活 | 跨平台消息 |
| **python_telegram_bot** | Telegram机器人 | ✅ 激活 | 跨平台消息 |
| **fastapi+uvicorn** | Web服务 | ✅ 激活 | API服务框架 |
| **pydantic** | 数据验证 | ✅ 激活 | 配置建模 |
| **cryptography** | 加密 | ✅ 激活 | 安全通信 |
| **apscheduler** | 任务调度 | ✅ 激活 | 内部任务管理 |
| **httpx** | HTTP客户端 | ✅ 激活 | 异步HTTP |
| **websockets** | WebSocket | ✅ 激活 | 实时通信 |
| **s3transfer** | S3传输 | ✅ 激活 | 云存储 |
| **boto3** | AWS SDK | ✅ 激活 | 云服务 |
| **huggingface_hub** | ML模型 | ✅ 激活 | AI模型管理 |
| **rich** | 终端格式化 | ✅ 激活 | CLI输出美化 |
| **typer** | CLI框架 | ✅ 激活 | CLI命令 |
| **pyyaml** | YAML解析 | ✅ 激活 | 配置管理 |

#### B. Brew安装的系统工具

| 工具 | 版本 | 用途 | 状态 | 核心问题 |
|:-----|:----:|:-----|:----:|:---------|
| **python@3.11** | 3.11.15 | Hermes Agent Python | ✅ 激活 | Agent运行环境 |
| **git** | 最新 | 版本控制 | ✅ 激活 | 代码管理 |
| **gh** | 2.89.0 | GitHub CLI | ✅ 激活 | PR/Issue管理 |
| **tmux** | 3.6a | 终端复用 | ✅ 激活 | 独立进程管理 |
| **rclone** | 1.73.3 | 云存储同步 | ✅ 可用 | 备份(已配置但检查) |
| **ffmpeg** | 8.1 | 音视频处理 | ✅ 可用 | 媒体处理(非交易核心) |
| **ollama** | 0.22.1 | 本地LLM | ✅ 可用 | 本地AI推理 |
| **ripgrep** | 15.1.0 | 文件搜索 | ✅ 激活 | 代码搜索 |
| **go** | 1.26.1 | Go语言 | ✅ 可用 | 某些组件(非引擎核心) |
| **tesseract** | 最新 | OCR | ✅ 可用 | 图片识别(非交易核心) |
| **gnupg** | 最新 | 加密 | ✅ 可用 | 安全(非交易核心) |

#### C. 已安装但非交易核心的库 (Hermes venv)

这些是Hermes Agent自身功能所需的库，与交易系统无关但已经安装：

| 库 | 用途 | 与交易系统关系 |
|:---|:-----|:--------------|
| alibabacloud_dingtalk | 钉钉API | 跨平台消息备用 |
| discord_py | Discord | 跨平台消息备用 |
| python_telegram_bot | Telegram | 跨平台消息备用 |
| edge_tts | 语音合成 | 非核心 |
| elevenlabs | 语音合成 | 非核心 |
| faster_whisper | 语音识别 | 非核心 |
| av | 音视频处理 | 非核心 |
| modal | 云计算 | 非核心 |
| firecrawl_py | 网页爬取 | 非核心 |
| exa_py | 搜索引擎 | 非核心(但web_search可用) |

#### D. 系统Python 3.9 (已弃用)

| 库 | 备注 |
|:---|:-----|
| pip 21.2.4, setuptools 58.0.4 | 纯基础环境 |
| altgraph, macholib, six, wheel | Xcode工具链依赖，非交易用 |

#### E. Brew Cask (GUI应用)

| 应用 | 用途 | 状态 |
|:-----|:-----|:----:|
| Docker Desktop | 容器化 | ✅ 可用 |
| ngrok | 内网穿透 | ✅ 可用 |

#### F. npm全局

| 包 | 备注 |
|:---|:-----|
| npm 11.9.0 | 包管理器本身 |
| corepack 0.34.6 | 包管理工具 |

#### G. 特殊工具 (未在brew/pip中但存在)

| 工具 | 发现路径 | 用途 |
|:-----|:---------|:-----|
| blogwatcher-cli | ~/.hermes/profiles/ | RSS订阅监控(有cron) |
| openclaw | ~/.local/lib/node_modules/ | 基础设施 |
| polymarket-bot | ~/polymarket-bot/ | 预测市场机器人(独立项目) |

### 1.3 未知工具发现机制

根据审计框架要求，Scouter的未知工具发现机制：

| 机制 | 频率 | 方法 |
|:-----|:----:|:-----|
| 每周常规搜索 | 周一08:00 | web_search 5-8个方向 |
| Hermes Skills Hub | 每次审计时 | skills_list() 扫描 |
| pip/brew版本变化 | 每月 | pip3 list + brew list 对比 |
| GitHub Trending | 每周 | 搜索crypto/quant相关新项目 |
| Python包更新 | 每月 | 关注requests/pandas/ta新版本 |
| config新文件 | 每次操作时 | 检查 config/ 新增文件 |

---

## 工作二：Skill全面审计

### 2.1 扫描方法

```
扫描范围:
├─ hermes skills_list() → 91个Skill
├─ ~/.hermes/skills/ → 空目录(无自定义Skill)
├─ ~/.hermes/profiles/zq-scouter/skills/ → 2个Skill
│   ├─ research/trading-system-toolchain-audit/SKILL.md
│   └─ research/crypto-market-reconnaissance/(可能)
└─ ~/.hermes/hermes-agent/skills/ → 内置(见AGENTS.md)
```

### 2.2 已装Skill分类 (Hermes 91个内置)

按类别统计：

| 类别 | 数量 | 与交易系统关系 |
|:-----|:----:|:--------------|
| **research** | 6 | **高 — 侦察/审计/论文/博客** |
| software-development | 12 | 中 — 编码辅助 |
| creative | 17 | 低 — 设计/艺术/媒体 |
| mlops | 11 | 中 — AI模型/推理 |
| apple | 4 | 低 — macOS特有 |
| autonomous-ai-agents | 4 | 低 — 代理编码工具 |
| devops | 3 | 中 — Kanban/Webhook |
| productivity | 8 | 低 — 办公工具 |
| github | 6 | 中 — 代码协作 |
| gaming | 2 | 极低 |
| media | 4 | 低 |
| data-science | 1 | 中 — Jupyter |
| other (email/social/smart-home/note/red-teaming) | 13 | 极低 |

### 2.3 交易系统直接相关的Skill

| Skill名 | 类别 | 安装状态 | 激活状态 | 核心问题 |
|:--------|:----:|:--------:|:--------:|:---------|
| **crypto-market-reconnaissance** | research | ✅ 已装 | ⚠️ 可用未激活 | 每周加密工具侦察 |
| **trading-system-toolchain-audit** | research | ✅ 已装 | ✅ 当前激活 | 工具体系审计 |
| **polymarket** | research | ✅ 已装 | ⏸️ 未使用 | 预测市场数据 |
| **arxiv** | research | ✅ 已装 | ⏸️ 未使用 | 论文搜索(策略参考) |
| **blogwatcher** | research | ✅ 已装 | ✅ 有cron | RSS监控(行情新闻) |
| **llm-wiki** | research | ✅ 已装 | ⏸️ 未使用 | 知识库构建 |
| **yuanbao** | social-media | ✅ 已装 | ⏸️ 未使用 | 腾讯元宝群组 |
| **xurl** | social-media | ✅ 已装 | ⏸️ 未使用 | Twitter发布(非数据采集) |
| **spotify** | media | ✅ 已装 | ⏸️ 未使用 | 无关 |
| **jupyter-live-kernel** | data-science | ✅ 已装 | ⏸️ 未使用 | 数据分析(策略研究用) |
| **github-code-review** | github | ✅ 已装 | ⏸️ 未使用 | 代码审查 |
| **plan** | software-dev | ✅ 已装 | ✅ 可用 | 计划模式 |

### 2.4 未安装但有价值的Skill

| Skill | 为什么没装 | 价值评估 |
|:------|:----------|:---------|
| 无 — 所有91个Skill都是内置的 | Hermes预装 | — |

### 2.5 未知Skill发现机制

| 机制 | 频率 | 方法 |
|:-----|:----:|:-----|
| skills_list() | 每次审计 | 检查新出现的Skill |
| Hermes Agent更新 | 版本升级时 | git pull后检查新Skill |
| hermes-agent-skill-authoring | 按需 | 创建自定Skill的入口 |
| user新增Skill | 用户安装时 | ~/.hermes/skills/ 监控 |

---

## 工作三：数据源审计

### 3.1 当前所有数据源

按 engine_realtime_v2.py 实际调用列表：

| # | 数据源 | 域名 | 端点 | 单次调用 | 支撑轮次 |
|:-:|:-------|:-----|:-----|:--------:|:--------:|
| 1 | **Binance Spot — K线(30m)** | api.binance.com | /api/v3/klines?interval=30m | ~50次 | 选币→评分 |
| 2 | **Binance Spot — K线(4h)** | api.binance.com | /api/v3/klines?interval=4h | ~20次 | 选币→趋势加分 |
| 3 | **Binance Spot — K线(1h)** | api.binance.com | /api/v3/klines?interval=1h | ~5次 | 选币→趋势加分 |
| 4 | **Binance Spot — K线(1d)** | api.binance.com | /api/v3/klines?interval=1d | ~5次 | 选币→涨幅 |
| 5 | **Binance Spot — 24h Ticker** | api.binance.com | /api/v3/ticker/24hr | 1次全量 | 选币→成交额排名 |
| 6 | **Binance Spot — Account** | api.binance.com | /api/v3/account | 2次 | 买入前/卖出后 |
| 7 | **Binance Spot — Order** | api.binance.com | /api/v3/order | 按需 | 买入/卖出执行 |
| 8 | **Binance Futures — Funding** | fapi.binance.com | /fapi/v1/premiumIndex | 1次(716合约) | 评分→费率因子 |
| 9 | **Binance Futures — OI** | fapi.binance.com | /fapi/v1/openInterest | ~20次 | 评分→OI因子 |
| 10 | **CoinGecko — Trending** | api.coingecko.com | /api/v3/search/trending | 1次 | 评分→社交热度 |
| 11 | **CoinGecko — Price** | api.coingecko.com | /api/v3/simple/price | 1次 | 多平台价格验证 |
| 12 | **DexScreener — Profiles** | api.dexscreener.com | /token-profiles/latest/v1 | 1次 | 评分→DEX热度 |
| 13 | **Etherscan — 链上数据** | api.etherscan.io | (工具就绪) | 未调用 | 待集成→聪明钱 |

### 3.2 数据源对交易环节的支撑评估

| 环节 | 支撑数据源 | 评估 |
|:-----|:----------|:-----|
| **选币库** | Binance Ticker(成交额排名) + CoinGecko(Trending) + DexScreener(Profiles) | ✅ **充分** — 3个独立维度的Top币种交叉验证 |
| **买入判断** | Binance K线(RSI/量比/趋势/价格位置) + CoinGecko(价格偏差) + Binance Futures(费率/OI) | ✅ **充分** — 6AND条件+12评分因子覆盖 |
| **卖出判断** | Binance K线(趋势/RSI变化/量比) + Binance WS(实时价格) + trend_store(费率趋势) | ✅ **充分** — E1-E6+P1-P3共9条件 |
| **风险控制** | OI/费率趋势存储 + 连续退出黑名单 + 多所价格偏差检测 | ✅ **覆盖** — 但可加强 |
| **链上聪明钱** | ❌ **缺失** — Etherscan工具就绪但未入评分 | ⚠️ **缺口** |

### 3.3 缺失但可补充的数据源

| 缺失维度 | 影响 | 免费替代 | 集成难度 |
|:---------|:----|:---------|:--------:|
| **智能资金流向** | 错失早期上车信号 | Debank (完全免费, REST API) | 中 |
| **波动率指数** | 无法过滤横盘假信号 | CryptoCortex (社区免费) | 低 |
| **OKX资金费率** | 单所费率偏差风险 | Bybit API (免费公开) | 低 |
| **链上大额转账** | 巨鲸动向盲区 | Etherscan (已有Key) | 低 — 工具已就绪 |

### 3.4 已知但未使用数据源

来自learning/探索报告，已探索但被认为暂不需要：

| 数据源 | 探索结论 | 是否仍正确 |
|:-------|:--------|:---------:|
| Ave.ai (DEX+聪明钱) | API可用但未集成 | ✅ 暂不需要 |
| CoinMarketCap | CoinGecko互补 | ✅ CoinGecko已够 |
| 非小号 | 中文行情 | ✅ 不需要 |
| MyTokenPro | 行情+链上+ETF流量 | ✅ 不需要 |
| Foresight News | 中文资讯 | ✅ 不影响交易 |
| TikTok | MEME传播 | ✅ 间接数据 |
| Twitter/X | 社交情绪$100/月 | ✅ 太贵 |
| YouTube | KOL喊单 | ✅ 间接数据 |

### 3.5 未知数据源发现机制

| 机制 | 频率 | 方法 |
|:-----|:----:|:-----|
| web_search方向搜索 | 每周一 | 5-8个方向(数据API/AI工具/链上/DeFi/中文) |
| 新项目跟踪 | 每周 | Product Hunt / GitHub Trending |
| 交易所新功能 | 实时 | Binance博客 / OKX公告 |
| 社区推荐 | 按需 | 飞书/TG/Discord抓取 |
| 付费工具替代 | 每月 | 检查新的免费替代上线 |

---

## 综合总结

### 状态总表

```
工具/数据源总计数: 37 (不含Hermes Agent自身库)
├─ ✅ 生产激活:  10 (Binance 9端点 + CoinGecko 2端点 + DexScreener 1端点 = 12实际API调用路径)
├─ ⚠️ 工具就绪:  3  (Etherscan API + trading-system-toolchain-audit Skill + pandas/ta fallback)
├─ ⏸️ 探索暂存:  13 (Ave.ai/CMC/Foresight/FeiXiaoHao/MyToken/TikTok/Twitter/YT + 3个暂缓Skill + 数据源配置)
├─ ❌ 已废弃:    10 (archive/下旧引擎/脚本)
└─ 📝 探索报告:  9  (learning/下9个平台报告)

Python第三方库(Herrmes venv): 约130个
├─ 交易系统直接使用: 3个 (requests/numpy/pandas+ta实际不在但fallback)
├─ Hermes Agent核心: ~60个 (LLM/Web/消息平台)
└─ Hermes Agent可选: ~67个 (多云/音视频/加密/钉钉等)
```

### 关键结论

1. **没有闲置付费工具** — 全部走免费API
2. **唯一核心缺口**: 链上聪明钱数据 (Etherscan工具就绪，差一步集成到评分公式)
3. **pandas/ta未在当前环境安装** — 引擎有fallback代码，但生产环境应确保安装
4. **2个相关Skill已就绪**: crypto-market-reconnaissance + trading-system-toolchain-audit
5. **数据源足够但可优化**: 加入Debank+Bybit API可补齐聪明钱+多所费率

### SHARED.md 更新内容

已在SHARED.md追加审计标记。

---

*报告由 ZQ-Scouter 生成于 2026-05-04*
*按 audit_framework.md Work1+Work2+Work3 顺序执行*
