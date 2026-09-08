import datetime

line = '|||2026-05-20 03:32:00|BUY|TON|10.8500|$2.0260|加仓TON(STRONG信号61pts)|A3:无今日报告|进攻型规则:A3无推荐,从STRONG最高分自选。ZEC(67pts)需清仓换位,改加仓已持TON(61pts,STRONG,layer1)。TON趋势15mUP/1hSIDE/4hSIDE,RSI1h=48/4h=57健康,独立于BTC+4%,成交量正常|A4质疑:凌晨03:32低流动性时期,但TON做市商活跃+STRONG信号技术面确认,普通仓位按规则执行|执行价$2.026,滑点0%,FILLED获10.85TON|持仓管理:DASH($43.10,SIGNAL54,RSI56,15mDOWN/1hSIDE/4hSIDE)HOLD, TON(新加仓~$57.10,STRONG61,RSI57,15mUP)HOLD, AR($64.62,SIGNAL44,RSI44,15mDOWN/1hSIDE/4hSIDE)HOLD, WLD/UNI/XEC尘仓minNotional锁HOLD|USDT~$130.28|FK:veto=false|空转:正常(距上笔BUY~3.5h)|进攻型:本轮执行了买入(加仓TON),遵循每轮必评估原则'

with open('/Users/lidaosong/zq_web4_trading_system/TRADES.md', 'a') as f:
    f.write('\n' + line + '\n')

print('TRADE record appended OK')
