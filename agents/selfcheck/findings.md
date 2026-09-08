# ZH系统自检报告 — 2026-09-04 07:05 BJT

**检查范围：** Cron存活 / 核心数据时效 / 交易引擎周期 / 余额仓位
**数据源：** AWS(15.134.211.154) crontab+logs+Binance公开API + 本地 ~/.hermes/cron/jobs.json + data/ 文件mtime

## 状态总览：⚠️ 基本健康，2项需关注（TON腿失效 + 文档滞后）

## 详细检查
1. **Cron**：✅ AWS crontab 25项全活（radar_v2/htx_loop/binance_band每5分、htx_recenter每30分、daily_review/risk_report 06:00 BJT今晨已跑0错误、备份4:00/16:00）。本地Hermes 68任务在跑（executions.db 07:02跳动）。⚠️ 昨日09-03晚间5个LLM类cron报HTTP 402余额不足（系统反思/健康扫描/A5复盘/行业扫描/每日简报），今晨已恢复（本自检正常运行），需观察今日18:00简报。
2. **数据**：✅ node_history.jsonl 07:00、signals.json 06:48、coin_pool.json 06:46、TRADES.md 06:31、ssh_watchdog 07:00(SSH OK)、aws_snapshot 05:00，全部新鲜。
3. **引擎**：✅ 实盘=binance_band(TON/ZEC波段,09-04新定案)+htx_loop(UNI/SUI)+radar_v2(扫描)。grid_bot已按crontab注释「2026-09-04老李定案」停用（02:35 BJT止，非故障）。radar 0错误。⚠️ binance_band自02:38启动起TON腿222次下单失败「Market is closed」——TONUSDT在币安状态=BREAK停牌，TON价格冻结$1.60；ZEC腿正常（现价$950.5，买$920/$880挂单2个，卖$1010/$1060）。htx_loop 09-03 16:35-16:45 UTC段KeyError 'buy1'反复崩溃后自愈，现4单正常。
4. **账户**：✅ 币安≈$218（USDT可用168.39+ZEC买单冻结40.48+尘），≈昨21:00收盘$218.33(+0.52%)无异动；HTX≈$107.6（UNI/SUI四买单，可用29.67+冻结77.90）；双所合计≈$326。昨币安15笔ETH卖出$187@2402-2416后ETH涨至~$2505（卖早约4%，观察项）。市场大涨：BTC$81.4K(+5.3%) ETH$2499(+4.7%) F&G 65。

## 问题清单
1. ⚠️ **TON腿完全失效**：09-04定案TON/ZEC波段，但TONUSDT处于BREAK（币安停牌），自启动起零成交；$168 USDT闲置、仅ZEC腿$40参与。需Commander确认：等恢复 or 调整。
2. ⚠️ **文档滞后**：09-04定案只写在crontab注释，CHANGE_LOG.md停更于08-31、NAVIGATION.md仍写grid_bot为主策略——其他Agent易按旧文档误判（本自检初判grid_bot停摆为故障，查注释后纠正）。
3. ℹ️ 昨日5个LLM cron 402失败，观察今日是否复发。
4. ℹ️ ETH卖早4%+TON停牌=新策略首日仅ZEC单腿运行，成效待验证期观察。

## 自检结论
系统基础设施健康：AWS三引擎按周期运行、数据全新鲜、账户无异常、双所≈$326。核心关注=09-04新定案的TON腿因币安停牌空转+文档未同步，建议Commander今日处理并同步NAVIGATION/CHANGE_LOG。
