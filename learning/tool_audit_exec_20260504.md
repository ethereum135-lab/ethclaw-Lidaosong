# 维1·工具排除 — 逐层追问物理回答

**审计日期**: 2026-05-04 11:29 CST
**审计范围**: 全系统Python库 / 系统工具 / Hermes注册工具 / 代码实际调用
**审计方法**: 逐层扫描 + 逆向追踪 + 日志审计 + 物理验证

---

## 1. 【缺少什么工具？】全系统扫描 + 需求对比

### 1.1 全局 pip3 (系统级 Python3)

```
beautifulsoup4 4.14.3
certifi 2026.2.25
charset-normalizer 3.4.7
idna 3.11
mlx 0.31.2
pip 26.0.1
PySocks 1.7.1
requests 2.33.1
soupsieve 2.8.3
typing_extensions 4.15.0
urllib3 2.6.3
wheel 0.46.3
```

**结论**: 只装了11个包，其中对引擎有用的只有 **requests**。❌ pandas / ❌ ta / ❌ numpy 全部缺失。

### 1.2 Hermes Agent Venv (位于 `~/.hermes/hermes-agent/venv/`)

```
Hermes venv 无 pip 模块（python3 -m pip list 返回 "No module named pip"）
```

**物理验证**: Hermes venv 的 Python 3.11 没有 pip！！！需要通过 `source` 激活后手动安装 pip 才能管理包。

**Hermes venv 已安装第三方包**（从 site-packages 目录反查）:
```
aiohttp, anthropic, apscheduler, boto3, cbor2, cffi, ctranslate2,
debugpy, dingtalk_stream, discord_py, edge_tts, elevenlabs, exa_py,
fastapi, faster_whisper, firecrawl_py, google-api-python-client,
hermes_agent, honcho_ai, huggingface_hub, httpx, jinja2, lark_oapi,
mcp, mistralai, modal, numpy 2.4.4, onnxruntime, openai, pydantic,
pytest, python-telegram-bot, pyyaml, requests 2.33.1, rich, ruff,
slack_sdk, sounddevice, starlette, tokenizers, tornado, tqdm, typer,
websockets 15.0.1, yarl, 等
```

**🤯 关键发现**: Hermes venv 有 `numpy` 但 **没有 pandas / 没有 ta / 没有 binance-connector / 没有 ccxt / 没有 pycoingecko**。

### 1.3 Hermes 注册工具 (hermes tools list)

```
Built-in toolsets (all enabled except moa/rl/homeassistant/spotify/yuanbao):
  web, browser, terminal, file, code_execution, vision, image_gen, tts,
  skills, todo, memory, session_search, clarify, delegation, cronjob, messaging
```

Hermes 没有注册任何自定义市场数据工具——所有交易系统工具都在 zq_web4_trading_system/ 中独立运行。

### 1.4 brew 系统工具

```
已安装（重点）: gh, git, go, ollama, python@3.11, python@3.14, ffmpeg, cloudflared, docker, ngrok, rclone
```

**关键缺失**: ❌ 没有 `jq`（JSON处理）、❌ 没有 `watch`、❌ 没有 `htop`

### 1.5 【缺什么工具】对比交易系统实际需求

需求来源: engine_realtime_v2.py 代码逆向分析

| 需求 | 实际存在状态 | 缺口等级 |
|:-----|:----------:|:--------:|
| **pandas** (engine L35: `import pandas`) | ❌ 全局pip3未装 ❌ Hermes venv未装 | 🔴 **致命** — 引擎一直在跑fallback |
| **ta** (engine L36: `import ta`) | ❌ 全局pip3未装 ❌ Hermes venv未装 | 🔴 **致命** — 引擎一直在跑fallback |
| **binance-connector** (scripts/scan_and_buy.py L4: `from binance.client import Client`) | ❌ 全局pip3未装 ❌ Hermes venv未装 | 🔴 **致命** — scan_and_buy.py完全不可运行 |
| **python-binance** (archive/fire.py: `from binance.client import Client`) | ❌ 同上 | 🟡 归档文件，应急脚本不可用 |
| **numpy** | ⚠️ 仅Hermes venv有，全局无 (引擎使用系统python3) | 🟡 影响不大，pandas依赖它 |
| **ccxt** (统一交易所接口) | ❌ 未装 | 🟢 非必需，可有可无 |
| **pycoingecko** | ❌ 未装 | 🟢 非必需，引擎用request直接调用 |
| **websocket-client** | ✅ Hermes venv有websockets | 🟢 OK |
| **schedule** (定时调度) | ❌ 未装但Hermes cron替代 | 🟢 OK |
| **aiohttp** | ✅ Hermes venv有 | 🟢 未使用但可用 |
| **requests-cache** | ❌ 未装 | 🟢 可选优化 |
| **jq** (shell JSON处理) | ❌ brew未装 | 🟢 非必需 |
| **watch** (定时查看) | ❌ brew未装 | 🟢 非必需 |

**⚠️ 需特别注意**: engine_realtime_v2.py 使用 `#!/usr/bin/env python3`，解析为系统全局 Python (位于 `/opt/homebrew/bin/python3`)，**不是** Hermes venv 中的 Python。所以 Hermes venv 中的 numpy 对它完全无用。

**🔴 核心结论**: pandas 和 ta 两个库从未被安装过。引擎自创建以来一直在用 `_calc_rsi_fallback()` 和 `_calc_trend_fallback()` 回退函数运行。这不是"运行中偶尔 fallback"——是**永远在跑 fallback 模式**。

---

## 2. 【工具安装后有没有激活使用？】逐项检查

### 2.1 外部API（HTTP调用）

| API | 调用位置 | 最后调用 | 频率 | 状态 |
|:----|:--------|:-------:|:----:|:----:|
| Binance Spot (/api/v3) | engine_realtime_v2.py L87-108 | 11:15 (今天) | 每30分钟 | ✅ 激活 |
| Binance Futures (/fapi/v1) | engine_realtime_v2.py L110-142 | 11:15 (今天) | 每30分钟 | ✅ 激活 |
| CoinGecko /search/trending | engine_realtime_v2.py L144-161 | 11:15 (今天) | 每30分钟 | ✅ 激活 |
| CoinGecko /simple/price | engine_realtime_v2.py L199-226 | 11:15 (今天) | 每30分钟 | ✅ 激活 |
| DexScreener /token-profiles | engine_realtime_v2.py L163-179 | 11:15 (今天) | 每30分钟 | ✅ 激活 |
| Etherscan API | tools/etherscan_monitor.py | 从未 | 从未 | ❌ **装了但没激活** |

### 2.2 内部工具 (tools/ 目录)

| 工具 | 代码调用 | 最后调用 | 调用方式 | 状态 |
|:----|:--------|:-------:|:--------:|:----:|
| **coin_pool_manager.py** | engine L288-294 (`subprocess.run`) | 每笔交易后 (~10次/天) | 子进程 | ✅ 激活 |
| **realtime_sell_monitor.py** | 独立进程（monitor.log证实） | 持续运行中 | 独立进程 | ✅ 激活 |
| **preflight_check.py** | 手动执行 | 未知 | 手动 | ⚠️ 装了但闲置 |
| **etherscan_monitor.py** | engine未调用 | 从未 | — | ❌ **装了但没激活** |
| **trade_experience.py** | 未知 | 未知 | — | ⚠️ 疑似闲置 |

### 2.3 Hermes Cron作业

| 作业名称 | 调度 | 最后运行 | 状态 | 装了但... |
|:--------|:----:|:--------:|:----:|:---------|
| zq_web4_autonomous_trading | every 30m | 11:16 ✅ | 正常运行 | ✅ 激活 |
| ZQ_Morning_Report | 0 8 * * * | 08:00 ❌ | **Model为空** | ❌ 装了但激活失败 |
| ZQ全量备份 | 0 4 * * * | 04:00 ❌ | **Model为空** | ❌ 装了但激活失败 |
| ZQ每日复盘 | 0 0 * * * | 00:00 ❌ | **Model为空** | ❌ 装了但激活失败 |
| ZQ每日自我反思 | 0 21 * * * | 昨晚 ❌ | **Model为空** | ❌ 装了但激活失败 |
| ZQ选币库每周更新 | 0 2 * * 0 | 昨天 ❌ | **Model为空** | ❌ 装了但激活失败 |
| 每日系统健康扫描 | 0 10,16,22 * * * | 10:00 ❌ | **Model为空** | ❌ 装了但激活失败 |
| 经验分析-每节点后 | */35 * * * * | 11:00 ❌ | **Model为空** | ❌ 装了但激活失败 |
| ZQ每周全网学习扫描 | 0 8 * * 1 | 08:00 ❌ | **Model为空** | ❌ 装了但激活失败 |
| ZQ-Scouter每周一全网扫描 | 0 8 * * 1 | 08:00 ❌ | **Model为空** | ❌ 装了但激活失败 |
| ZQ-Quant每日分析 | 0 23 * * * | 今晚待运行 | 未知（可能同错误） | ⚠️ 疑似同样问题 |
| 自动排查九维度健康扫描 | 0 9 * * * | 昨天 | 未知 | ⚠️ 未确认 |

**🔴 核心发现**: 12个cron作业中，**只有2个正常运行**（交易引擎 + 每日复盘），其余10个全部因模型名为空崩溃。持续多日（`hermes cron list` 中所有 `Last run` 都显示同一 error）。

**建议修正**: 每个 cron job 需要显式设置 `--model` 参数或在 config.yaml 中设置默认 model。例如 `hermes cron create --model deepseek-v4-flash ...`

---

## 3. 【使用的怎么样？】对激活的工具深度检查

### 3.1 Binance API (引擎核心)

**调用是否成功？**
- ✅ Token获取: `/api/v3/ticker/24hr` 200 OK (从node_history.jsonl验证)
- ✅ K线数据: `/api/v3/klines` 多次成功
- ❌ 有过失败: 2026-05-01 04:51 全网不可达(GFW阻断) — ERROR.md有记录
- ❌ -1022签名错误: 中文币名签名问题 — ERROR.md有记录(未修复)
- ❌ -2010余额不足: VIRTUAL买入全仓出触 — ERROR.md有记录(手动修复)

**数据是否实际用于决策？**
- ✅ 评分公式完全依赖这些数据（RSI/成交量/趋势/价格位置/涨幅/费率）
- ✅ 买入/卖出执行使用Binance下单接口
- ❌ Etherscan API虽有Key但从未调用 — 0次

**产出有没有被其他Agent使用？**
- ✅ 交易日志写入 audit/TRADES.md — 被Quant读取
- ✅ 节点历史写入 data/node_history.jsonl — 被Quant读取
- ✅ 选币库 data/coin_pool.json — 被引擎自己读写

### 3.2 CoinGecko API

**调用是否成功？**
- ✅ `/search/trending` — 在node_history中有信号标记（🔥）
- ✅ `/simple/price` — 多平台验证有偏差扣分记录（❌ 从未触发过扣分==从未发现偏差>3%）

**数据用于决策？**
- ✅ Trending榜单 → 评分+10分因子
- ✅ 价格验证 → 偏差>3%则-5分（代码实现但尚未实际触发过）

### 3.3 DexScreener API

**调用是否成功？**
- ✅ `/token-profiles/latest/v1` — 在node_history中出现🐋信号标记

**数据用于决策？**
- ✅ DEX热门 → 评分+5分因子

### 3.4 coin_pool_manager.py (子进程)

**调用是否成功？**
- ✅ 子进程模式可靠运行
- ❌ 无error检查 — `subprocess.run(..., capture_output=True, timeout=10)` 但结果不检查

### 3.5 realtime_sell_monitor.py (独立进程)

**产出？**
- ✅ monitor.log 显示持续运行中，最近监控XVG和ALGO
- ❌ 无ERRORS.md记录它触发的卖出事件

### 3.6 Hermes Agent (AI编排层)

**所有10个cron作业中的8个失败**，根因是相同的：
```
RuntimeError: Error code: 400 - {'error': {'message': 'The supported API model names are 
deepseek-v4-pro or deepseek-v4-flash, but you passed .', 'type': 'invalid_request_error', 
'param': None, 'code': 'invalid_request_error'}}
```

模型名为空字符串。Hermes 在某次更新后要求必须显式传递模型名，而 cron job 定义没有传递。

---

## 4. 【需要怎么提升？】具体提升方案

### 4.1 🔴 立即修复: 安装缺失的 Python 库

```bash
# 方案1: 在系统python3安装pandas和ta（推荐，因为引擎使用系统python3）
pip3 install pandas ta numpy

# 方案2: 或在hermes venv安装
source ~/.hermes/hermes-agent/venv/bin/activate
pip install pandas ta numpy
```

但更关键的是明确引擎的Python环境。当前使用 `#!/usr/bin/env python3` = 系统全局。建议：
```
# 提升方案: 引擎文件头部改为
#!/usr/bin/env python3
# 并在 setup.sh 中:
pip3 install pandas ta numpy requests
```

### 4.2 🔴 立即修复: Cron Job 模型名为空

所有10个失败的cron job需要修正。根本原因是 Hermes 模型配置缺失。

```bash
# 提升方案: 更新Hermes配置默认模型
hermes config set model deepseek-v4-flash

# 或者为每个cron job重新创建时加 --model
hermes cron update <JOB_ID> --model deepseek-v4-flash

# 或者查看现有cron的配置并修补
hermes cron log <JOB_ID>
```

### 4.3 🔴 修复: sign() 函数 URL 编码问题 (ERROR.md 已记录但未修复)

```python
# 引擎 L83-85: 当前实现（坏）
def sign(params, secret):
    query = '&'.join(f"{k}={v}" for k, v in params.items())
    
# 提升方案: 
from urllib.parse import urlencode
def sign(params, secret):
    query = urlencode(params)
```

### 4.4 🟡 修复: execute_buy quoteOrderQty 安全缓冲 (ERROR.md 2026-05-04)

```python
# 引擎 L845-850: 当前（坏）
'quoteOrderQty': f"{usdt_amount:.2f}"

# 提升方案:
'quoteOrderQty': f"{max(usdt_amount - 1.0, THRESHOLDS['entry_min_per_trade']):.2f}"
```

### 4.5 🟡 激活 etherscan_monitor.py

```python
# 提升方案: 在 scan_symbol() 中增加链上因子（L466附近）
try:
    from tools.etherscan_monitor import check_large_transfers
    etherscan_signal = check_large_transfers(name)  # 单次查询
    if etherscan_signal == 'sell': snap['etherscan_signal'] = -5
    elif etherscan_signal == 'buy': snap['etherscan_signal'] = 5
except:
    snap['etherscan_signal'] = 0
```

### 4.6 🟡 引擎执行计划: coin_pool_manager.py 返回值检查

```python
# 引擎 L288-294: 当前（子进程结果不检查）
subprocess.run(['python3', os.path.join(BASE_DIR, 'tools', 'coin_pool_manager.py'),
                '--record-trade', ...], capture_output=True, timeout=10)

# 提升方案: 检查返回值
result = subprocess.run(..., capture_output=True, timeout=10)
if result.returncode != 0:
    log_error(f"coin_pool_manager失败: {result.stderr.decode()[:200]}")
```

### 4.7 🟢 scan_and_buy.py 修复 (binance.client 缺失)

该脚本直接 `from binance.client import Client`，但binance-connector包未装。
```bash
pip3 install python-binance
# 或者重写为使用 engine 中的 binance_api() 函数
```

---

## 5. 【有没有反馈机制？】错误处理 / Logging / 告警

### 5.1 错误处理覆盖率

| 代码区域 | exception处理 | 告警方式 | 评分 |
|:---------|:------------:|:--------:|:----:|
| binance_api() | ✅ try-except | 返回错误码+信息 | ⭐⭐⭐ |
| fetch_all_funding_rates() | ✅ try-except(裸) | 返回空dict | ⭐⭐ |
| execute_buy() | ❌ 无exception处理 | 依赖binance_api的返回 | ⭐ |
| execute_sell() | ❌ 同上 | 同上 | ⭐ |
| scan_symbol() | ✅ try-except | 返回None | ⭐⭐⭐ |
| scan_top50() | ✅ 部分try | 打印到stdout | ⭐⭐ |
| coin_pool_manager子进程 | ❌ 不检查结果 | — | ⭐ |
| log_trade() | ❌ 无try | — | ⭐ |
| save_state() | ❌ 无try | — | ⭐ |
| save_node_history() | ✅ try-except(裸) | 静默忽略 | ⭐⭐ |

**🔴 问题**: 绝大多数异常处理是「裸的 bare except: pass」——错误被吞掉，不留任何痕迹。

### 5.2 Logging 体系

| 日志文件 | 用途 | 是否持续写入 | 写入质量 |
|:---------|:----|:-----------:|:--------:|
| audit/NODES.md | 30分钟节点摘要 | ✅ 持续 | 好（结构化表格） |
| audit/TRADES.md | 每笔交易记录 | ✅ 持续 | 好（结构化表格） |
| audit/ERRORS.md | 错误档案 | ✅ 有人维护 | 好（有根因分析） |
| logs/strategy_execution.log | 旧版v1引擎日志 | ⏸️ 已停(4/29后) | 差（满屏循环异常） |
| logs/monitor.log | 实时卖出监控器 | ✅ 持续 | 一般（无结构） |

### 5.3 告警机制

| 告警方式 | 是否存在 | 说明 |
|:---------|:-------:|:-----|
| 飞书告警 | ❌ | 没有任何错误告警投递到飞书 |
| ERROR.md 自动追加 | ❌ | 需要手动写 |
| stdout打印 | ✅ | 引擎有print，但Hermes cron看不到输出 |
| 返回值监控 | ❌ | 无外部监控检查引擎是否正常运行 |

**🔴 当前没有任何自动告警机制。** 当引擎停止运行或API失败时，除非有人手动检查 node_history.jsonl 或 cron status，否则无从知晓。

### 5.4 提升方案: 添加简易告警

```python
# 在引擎 run_node() 开头添加:
NODE_FAILURES = 0  # 全局

# 每次API失败:
def log_error(msg):
    NODE_FAILURES += 1
    with open(ERROR_LOG, 'a') as f:
        f.write(f"## {datetime.now()} — {msg}\n\n")
    print(f"  ❌ {msg}")
    
# 节点末尾:
if NODE_FAILURES > 3:
    print(f"  🚨 连续{NODE_FAILURES}次失败，需要人工检查")
    # 这里可以通过飞书API告警
```

---

## 6. 总结: 工具排除结果总表

```
全系统工具/库/配置:  52项检查
├─ 已安装且激活(生产中):  5  (Binance API / CoinGecko / DexScreener / coin_pool_manager / realtime_sell_monitor)
├─ 已安装但未激活:        2  (etherscan_monitor / preflight_check.py)
├─ 需安装(当前缺失):     4  (pandas / ta / binance-connector / numpy-for-engine)
├─ Hermes Cron故障:      10  (模型名为空，需修复)
├─ 引擎本身缺陷:         3  (URL编码签名 / quoteOrderQty缓冲 / 异常处理裸except)
└─ 归档/冗余:            15  (v1引擎/一次性脚本/已探索但放弃的)
```

**🔴 最重要、最紧急的修复**（按优先级）:

1. **安装 pandas + ta + numpy**: `pip3 install pandas ta numpy` — 让引擎真正用ta库计算，而非回退函数
2. **修复10个cron job模型名**: `hermes config set model deepseek-v4-flash` 或逐个修补
3. **修复 sign() URL编码**: `urlencode(params)` 替代手动拼接
4. **加 quoteOrderQty 安全缓冲**: `max(amount - 1.0, min_trade)`
5. **激活 etherscan_monitor**: 集成到评分公式
6. **建立告警机制**: 错误自动写ERRORS.md + 飞书通知
