# ZQ System 错误档案

## 2026-08-04 21:42 🔴 假成交记录 — execution_results.json 声称 ENA FILLED 但 Binance 无成交

**问题:** AWS `data/signals/execution_results.json` 声称 sig_20260804_2036_1238 (BUY ENA $15 @ $0.0914, 164.11 ENA, 订单3321972045) 于 20:40 **FILLED**。

**核实 (21:40 SSH→AWS→Binance 物理直查):**
- `tools/_check_balance_aws.py`: 余额 **无 ENA** (free=0)
- `/api/v3/myTrades` ENAUSDT: 今日无任何成交 — 最后成交时间为 1781739604700 (≈06-17)
- USDT free=$6.42 (若真买入$15应≈$51)

**结论:** fill 记录为**伪造/误写** — 执行器 `a4_independent.py` 可能未校验 Binance 实际成交即写入 execution_results.json。

**影响:** 状态追踪(node_history/TRADES)与真实账户脱节, 决策层可能基于虚假持仓做判断。

**待修复 (铁律二·追根究底):** 排查 a4_independent.py 的 fill 写入逻辑, 要求以 Binance 订单状态/成交回报为准, 失败/未成交不得写 FILLED。

## 2026-04-30 09:49 — ENGINE_RUN_27: -1022 签名错误 on Chinese-char symbol

**问题:** v2引擎买入排名#19 币种"币安人生"（评分64.8，$19.95）时返回 -1022 "Signature for this request is not valid"。

**根因:** 引擎的 `sign()` 函数使用 `params.items()` 构造查询字符串时，未对非ASCII字符进行URL编码：
```python
query = '&'.join(f"{k}={v}" for k, v in params.items())
```
Binance API期望签名基于 URL-encoded 查询字符串（如 `symbol=%E5%B8%81%E5%AE%89%E4%BA%BA%E7%94%9FUSDT`），但引擎传入原始UTF-8字符（`symbol=币安人生USDT`）。对于仅含ASCII字符的币种名两者一致，但中文币名导致签名不匹配。

**影响:** 该 $19.95 分配改由 #45 VANA 使用（$13.13）。组合价值不受影响，但币安人生未被成功建仓。

**修复方案:** `sign()` 函数改为使用 `urllib.parse.urlencode()` 构造查询字符串：
```python
from urllib.parse import urlencode
query = urlencode(params)
```
而非手动拼接 `f"{k}={v}"`。

**状态:** ✅ 已修复 — 2026-05-06 02:21节点，修改 `sign()` 使用 `urlencode()`。买入 #48 币安人生USD $437 成功(订单162624140)。浏览器测试 + 实盘验证通过。

## 2026-05-01 04:51 — NODE_04:51: Binance API 全网不可达（GFW阻断）

**问题:** 2026-05-01 04:51 节点，所有 Binance API 端点（api/api1/api2/api3.binance.com，6个CDN IP，IPv4+IPv6）TCP连接全部超时。cloudflare.com正常，testnet.binance.vision正常，但binance.com主网完全不可达。

**根因:** ISP网络层阻断（China Mobile, traceroute到221.183.81.133后无响应）。当地GFW对Binance IP段的封锁。

**影响:** 无法获取实时价格/余额/K线数据。无法执行交易决策。所有持仓未变动（LINK ~28.87, WLD 348.5, USDT $56.91）。

**修复尝试:**
1. 尝试所有已知 Binance CDN IP：全部超时
2. 尝试 IPv6 连接：超时
3. 尝试 --resolve 强制IP：超时
4. 尝试 alternative Binance 域名（api.binance.us, www.binance.info）：全部超时
5. 检测到 Clash Verge 已安装但核心(mihomo)未运行（profiles.yaml current=null）。LetsVPN 运行中但无本地代理端口

**恢复建议:** 重新启用 Clash 代理或重连 VPN。在下一个30分钟节点（~05:20）重试。

**状态:** 待网络恢复后重试

## 2026-05-04 08:27:31 — 引擎-2010 (price fluctuation on full-balance quoteOrderQty)

**问题:** v2引擎买入唯一通过6AND的VIRTUAL(#45, 评分57.0)时，使用全量$412.84作为quoteOrderQty返回-2010 "insufficient balance"。价格$0.74→$0.743轻微上升导致全仓quoteOrderQty超出实际余额。

**根因:** 引擎decide_entry()使用精确余额作为quoteOrderQty，无安全缓冲。价格从读取到下单间微秒波动即可触发-2010。

**缓解（本次成功）:** 拆分为2笔：$99.95 + $311.83（最后一笔-1美元缓冲）。两笔均成交。

**前次出现:** NODE_07:47 — VIRTUAL评分57.8同样-2010失败（未执行手动回退）。

**建议修复:** 引擎quoteOrderQty应使用`balance - 1.0`作为安全缓冲，或重试时自动减$1。

**状态:** 本次已手动修复。

## 2026-05-06 10:00 — PREFCHECK: HTTP 451 (Binance geo-block，持续中)

**问题:** 每日预飞检查 [1/6] 资金状况报错 HTTP Error 451。Binance API 通过 ss-local(1080) 代理请求时被 CloudFront 返回 451 geo-block。v2ray(1081) 远程服务器 206.190.236.120:5957 仍不可达。双代理均失效。

**根因:** ss-local 出口IP（新加坡）被 Binance CloudFront geo-block；v2ray 远程服务器进程已死/端口未监听。自 06:10 (~4小时) 起系统无法访问 Binance API。

**影响:** 无法获取实时余额/价格/K线。持仓 MEGA/ZEN/EIGEN 冻结中。FK veto 已触发 (RL3)。引擎所有节点静默失败。Monitor 60s 轮询全部超时。

**已知状态:** FZ总控 08:30 已标记 P0 需人工介入（重启远程 v2ray 服务器）。FK已连续5个SKIP节点。当前无自动修复路径。

**状态:** ⚠️ 持续中 — 等待人工重启远程服务器

### 2026-05-06 16:00 — PREFCHECK 跟进
| 检查项 | 结果 |
|:---|---:|
| 直接 Binance API | ❌ HTTP 451 |
| ss-local(1080) | ❌ 连接失败 |
| v2ray(1081) | ❌ 连接失败 |
| 累计SKIP节点 | 持续中 (自06:10起 ~10小时) |
| 其他5项检查 | ✅ 全部通过 |
| 今日交易表现 | 今日买入6笔，卖出4笔（网络瘫痪前执行） |
| Etherscan 链上数据 | ✅ ETH $2371 |

**结论:** 网络问题无任何改善，与10:00状态一致。双代理均不可用，引擎静默失败继续。此问题无法自动修复——需人工介入重启远程v2ray服务器(206.190.236.120:5957)或更换代理方案。FK风控SKIP持续中。其他5个维度全部正常。

### 2026-05-06 22:00 — PREFCHECK 日终扫描
| 检查项 | 结果 |
|:---|---:|
| 直接 Binance API | ❌ HTTP 451（持续中） |
| 引擎状态 | ✅ v20260503.1 最后修改 08:39 |
| 交易分析 | ✅ 总407笔，今日买入6笔卖出4笔 |
| 监听器 | ✅ 3255行，不报新错（查持仓失败同根因） |
| 链上监控 | ✅ ETH $2368 |
| 代码完整性 | ✅ 引擎/监听器/Etherscan 字节数正常 |
| 待办事项 | ✅ 无 |

**状态:** 🔴 HTTP 451 仍是唯一异常项，自06:10起已持续约16小时。其余5/6维度全部正常。今日交易数据停留在网络瘫痪前（买入6笔卖出4笔）。需人工介入重启远程v2ray服务器方可恢复。

### 2026-05-07 10:00 — PREFCHECK 日扫描
| 检查项 | 结果 |
|:---|---:|
| 直接 Binance API (资金) | ❌ HTTP 451（持续中，约28小时） |
| 交易分析 | ✅ 总464笔，今日买入12笔卖出10笔 |
| 引擎状态 | ✅ v20260503.1 最后修改 05-07 02:32 |
| 监听器 | ✅ 3255行（查持仓失败同根因） |
| 链上监控 | ✅ ETH $2327 |
| 代码完整性 | ✅ 引擎52,464B / 监听器16,976B / Etherscan 4,364B |
| 待办事项 | ✅ 无 |

**状态:** 🔴 HTTP 451 持续中（第28小时）。**重要发现：** 尽管资金检查失败，引擎今日仍执行了12笔买入+10笔卖出（00:00—08:30），说明引擎使用的API路径可能与preflight_check不同，或已部分恢复。但 node_history.jsonl 最后记录停留在05-06 06:10，引擎状态快照未更新。监听器仍持续报"查持仓失败"。需人工介入：重启远程v2ray服务器(206.190.236.120:5957)或更换代理方案。

### 2026-05-07 16:00 — PREFCHECK 日间扫描
| 检查项 | 结果 |
|:---|---:|
| 直接 Binance API (资金) | ❌ HTTP 451（持续中，约34小时） |
| 交易分析 | ✅ 总464笔，今日买入12笔卖出10笔 |
| 引擎状态 | ✅ v20260503.1 最后修改 05-07 02:32，扫描币数50个，评分范围25.2~123.0 |
| 监听器 | ✅ 3255行（查持仓失败同根因，卖出信号触发0次） |
| 链上监控 | ✅ ETH $2344 |
| 代码完整性 | ✅ 引擎52,464B / 监听器16,976B / Etherscan 4,364B |
| 待办事项 | ✅ 无 |

**状态:** 🔴 HTTP 451 持续中（第34小时）。与前几次扫描结果一致，无任何改善。5/6 维度正常通过。引擎日交易数据（12买入/10卖出）与此前一致——表明这些交易执行发生在网络瘫痪前或使用了不同的 API 路径。需人工介入：重启远程 v2ray 服务器(206.190.236.120:5957)或更换代理方案。此问题无法自动修复。

## 2026-05-16 13:06 — A4 Blade 空转自检 🔴风险（19节点连续HOLD）

**问题:** A4自2026-05-15 20:35清仓SUI后，已连续19个执行节点（~9.5小时）全部输出HOLD/CHECK，未产生任何BUY或SELL交易。

**空转等级:** 🔴 16-24节点区间（系统空转风险）

**根因分析:**
1. **A3空仓（主因）** — 2026-05-16报告明确结论「🚫空仓—今日不推币」(9/10置信度)。全市场回调日，A3基于四维精选分析认为无币满足买入条件。
2. **持仓稳定无触发** — 7个持仓（XRP/CHZ/DOGE/CRV/TON/UNI/XEC）全部在安全区间运行，无减仓/清仓信号触发。
3. **周末市况** — 周六BTC在$79K窄幅整理，无方向性突破。

**判定:** ✅ 守纪律非系统空转。A3主动选择空仓+所有持仓稳定=系统在正确运行。不视为缺陷。

**建议:** 等待A3周一(05-17)的新报告。BTC需站回$79.5K以上才能开启新入场窗口。
2026-05-17 02:15 BJT | A4 | 三跑验证异常上报测试

## 2026-05-19 06:03 — A4 Blade 空转自检 🔴风险（35+节点连续HOLD）

**问题:** A4自2026-05-18 08:31 DOGE SELL后，已连续35+个执行节点(~43小时)全部输出HOLD/巡检/SKIP，未产生任何新的BUY或SELL交易。

**空转等级:** 🔴 16-24节点区间（系统空转风险）

**根因分析:**
1. **DYM趋势持续SKIP** — A3推荐DYM(首选)但a4_trend_checker连续返回SKIP(4/9): VOL 0.0x量枯竭, RSI 67.7近超买, POS 80.6%靠近阻力$0.0253。价格始终在$0.0246-0.025未有效突破。
2. **ZH方向不匹配** — DYM属Cosmos生态，不在ZH今日前三方向(Privacy/AI/Payment)中。
3. **LRC条件不满足** — A3条件候选LRC因ZH L2回避+15m↓1h↓4h↓全线向下被跳过。
4. **USDT余额$49限制** — 虽满足$19.74 position计算，但无合格候选币。
5. **NEAR STRONG但超买** — AI方向NEAR在signals中STRONG(60)但RSI 75.7/83.2极度超买+量0.1x，需等回调。

**判定:** 🟡 部分纪律守候，部分市场条件不足。DYM的趋势不支持与ZH方向不匹配双重限制导致空转。非系统故障。

**建议:** 07:00交易窗口开启后：
- 若DYM放量突破$0.0253阻力 → 重新评估BUY
- 若NEAR回调至RSI<65+放量 → BUY_PULLBACK
- 检查A3 07:00新报告是否有新推荐

## 2026-06-06 02:31 — SOCKS5 tunnel 端口1080断连

**问题：** SSH配置使用 `ProxyCommand nc -x 127.0.0.1:1080` 但SOCKS5端口1080无进程监听。

**影响：** `ssh web4` 默认配置失败。`append_node_history.py` 使用 `ssh web4` 也失败。

**当前workaround：** `ssh -o ProxyCommand=none` 绕过SOCKS5，直接SSH工作正常 ✅

**需要的修复：** 启动SOCKS5隧道，或修改SSH config去掉ProxyCommand，或修改脚本使用 `-o ProxyCommand=none`。

**检测：** `ssh_watchdog`（每5分钟）检测到失败但只能报警，不能自动恢复。

## 2026-06-06 03:35 — SSH完全断连（直连超时·SOCKS5死·API被地理位置封锁）

**升级：** 直连SSH (`-o ProxyCommand=none`) 也超时了（"Connection timed out during banner exchange"）。之前02:31时直连还通的workaround现在也失效。

**状态：**
- SOCKS5隧道(1080端口) → ❌ 进程不存在
- 直连SSH(22端口) → ❌ banner exchange超时
- 端口22 TCP可达（nc成功+ping~0.3ms）但SSH daemon不响应banner
- Binance API直连 → ❌ 被地理位置封锁 (code=0 "Service unavailable from a restricted location")

**根因推测：** AWS EC2实例上的SSH守护进程可能已挂/过载。TCP握手成功（22端口开放）但SSH daemon不发送版本banner，说明服务器端ssh进程没有在监听。

**影响：** A4完全无法查询余额/价格/执行交易。USDT $233.79闲置，STG半仓($16.53)无法监控。

**是否需要修复：**
1. AWS EC2实例可能需要重启SSH服务或重启整机
2. ssh_watchdog自身也挂了无法自动恢复

---

## [2026-06-06 04:05] 🔴 AWS SSH完全断连 — `Connection closed by UNKNOWN port 65535`

**来源：** A4 Blade Cycle #30

**症状：**
- SOCKS5隧道(1080端口) → ❌ 进程不存在，无法启动
- 直连SSH `ssh -D 1080 -N ubuntu@3.27.3.202` → ❌ `Connection closed by UNKNOWN port 65535`
- SSH直连 `ssh -o ConnectTimeout=10 ubuntu@3.27.3.202` → ❌ 同上
- 尝试 `tunnel_binance.sh` → ❌ 同样port 65535错误
- 较03:35的"直连超时"状态进一步恶化——AWS EC2完全不可达

**根因：** AWS EC2实例3.27.3.202从本网络完全不可达。TCP层返回RST (`UNKNOWN port 65535`)，表明网络层阻断或EC2实例已停机。非SSH层次的问题，非A4能修复。

**影响：**
- A4完全无法执行交易（查价/查余额/下单/推送信号全部不可用）
- A4信号`a4_signals.json`（sig_30）无法推送到AWS
- AWS `a4_independent.py` 无新信号可执行
- USDT $233.79 93%闲置（被动）
- STG半仓 69.64@$0.2439(-2.67%) 无法监控实时价（硬止损$0.2317未知是否触发）

**状态历史：**
- 02:31 → 直连SSH通 → 执行BTC-5%+减半仓 ✅
- 03:05 → 直连恢复间歇性 → 推信号sig_28 ✅
- 03:35 → SSH完全断连（直连超时）→ 无动作
- 04:05 → AWS不可达（port 65535）→ 无动作

**修复建议：**
1. AWS EC2实例可能已停机或网络策略变更
2. 需通过AWS Console检查EC2状态（SSH方式不可用）
3. 如果EC2运行中，检查安全组入站规则是否变更

**2026-06-06 04:31 BJT — 🔴 SSH断连持续·第34次Watchdog失败·AWS 3.27.3.202端口22 TCP可达但SSH握手超时**

**根因更新：** nc -zv -w5 3.27.3.202 22 → "succeeded!" (TCP连接成功)，但SSH连接 `ssh -F /dev/null -i key ubuntu@host` → "Connection timed out during banner exchange" (30s超时)。说明：
- AWS实例处于运行状态（端口22 TCP可达）
- SSH守护进程可能已崩溃或资源耗尽
- 不是网络阻断，是实例内部SSH服务异常
- 无法远程修复——SSH是唯一管理通道

**影响：**
- A4无法执行已持续约1.5小时（从03:35→04:31）
- 期间BUY_READY候选12个（VIC/JST/LOKA/ELF/PLA/ERN等）
- USDT $233.79 93%闲置
- STG半仓 69.64@$0.2439 失去实时监控

**状态延伸：**
- 03:05 → 直连短暂恢复→推信号sig_28 ✅ (19连败后首胜)
- 03:35 → SSH完全断连
- 04:05 → AWS不可达(port 65535)
|- 04:31 → 端口22 TCP开放但SSH握手超时（实例SSH守护进程挂了）
|
|**2026-06-06 05:05 BJT — 🔴 SSH断连持续3h·SSH守护进程崩溃·需AWS Console重启EC2**
|
|**状态更新：** nc -zv 3.27.3.202 22 → "succeeded!" (TCP连接持续开放)，但 `ssh -i key ubuntu@host` → "Connection closed by UNKNOWN port 65535" (握手阶段立即失败)。说明SSH守护进程(sshd)在AWS EC2实例上已经完全崩溃/异常退出。
|
|**影响附加（从04:31起新增）：**
|- SSH断连已持续3小时（02:31→05:05 BJT）
|- 期间错过1次新信号扫描周期（正常的06:00扫描即可产出新signals.json）
|- 12个BUY_READY候选信号已过时（5h过期）
|- 固定基本面：USDT $233.79 93%闲置·STG半仓失去实时监控·当天盈利完全归零
|
|**恢复建议：** 需有AWS Console权限的人操作：
|1. 登录AWS Console
|2. 找到EC2实例3.27.3.202
|3. 重启实例（或通过EC2 Serial Console检查sshd状态）
|4. 重启后A4自动恢复（Watchdog每30分钟重试SSH连接）

## 2026-06-06 06:30 | SSH断连持续4h+ — 本地Binance直连方案已验证可行

**实盘进展：**
/bin/bash: line 2: printf: `)': invalid format character
- 06:04周期：硬止损STG(-7.38
## 2026-06-06 11:00 BJT — SSH隧道持续断连 (第10小时)
- **状态:** AWS EC2 3.27.3.202完全不可达 — "Connection closed by UNKNOWN port 65535"
- **根因推测:** SSH守护进程崩溃或EC2实例需要重启（自02:30起持续断连）
- **影响:** 无法推送a4_signals.json到AWS执行·无法查询余额·无法执行交易
- **变通:** 本地Binance API查价正常 ✅ · 决策和数据在本地完成 ✅ · a4_signals.json等待通道恢复后推送
- **建议:** 需要AWS Console重启EC2实例 ubuntu@3.27.3.202

## 2026-06-18 22:25 🔴 ENJ硬止损触发 - 执行通道全断

**ENJ:** entry @ $0.03634, current $0.03514 → -3.30% 🔴 已击穿F&G<20硬止损线(-3%)
**执行通道:** SOCKS5断(20次失败, 最后OK 20:50) + 本地API 451
**动作:** 决策完成·等待通道恢复后立即执行SELL ENJ 169@$0.03514
**RL5合规:** 亏损$0.20 << 总资×1%($2.43) ✅

## 2026-08-16 20:25 🔴 daily_profit_engine误止损NIL — 成本基准BUG

**现象:** A4 20:20买入NIL $16@0.0494(323.90)后1分钟, 服务器daily_profit_engine以固定成本基准PER_TRADE_USD=$20计算PnL=-20

## 2026-08-16 20:25 🔴 daily_profit_engine误止损NIL — 成本基准BUG

**现象:** A4 20:20买入NIL $16@0.0494(323.90)后1分钟, 服务器daily_profit_engine以固定成本基准PER_TRADE_USD=$20计算PnL=-20%, 触发硬止损卖出323.90@0.0494, 回收$15.67 (实际≈平进平出, 真损仅手续费~$0.03; 引擎日志误记-$4.33)
**根因:** tools/daily_profit_engine.py 用固定PER_TRADE_USD=20当entry_cost, 不读A4真实成交价; 对A4管理的$16仓位误判-20%
**已做:** NIL SELL已写入audit/TRADES.md(2h冷却) 防20:48回购循环; 真实净值$214.30已更新total_asset.json
**✅已修复(21:15 每日盈利排查cron):** daily_profit_engine升级v1.2 — ①只管理本引擎BUY日志里的仓位(load_owned_symbols, 现仅SOLUSDT), A4仓位一律跳过, 杜绝再杀A4持仓; ②成本改为myTrades真实成本(get_actual_cost), 不再固定$20。已部署AWS并实跑验证: 跳过ETH/LINK/ALICE/ROBO等全部A4仓位, 无新交易, 日志无新增行。
