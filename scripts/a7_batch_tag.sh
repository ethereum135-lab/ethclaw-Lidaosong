#!/bin/bash
# A7 涨幅榜批量打标脚本
cd /Users/lidaosong/zq_web4_trading_system

# TOP10 必打标 (所有涨幅≥5%有清晰叙事的币)
python3 tools/enrich_coin.py --source A7 --symbol VICUSDT --tag '{"sentiment":"positive","narrative":"Viction Layer1公链引领涨幅榜，涨幅+65%成交量放量","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol CREAMUSDT --tag '{"sentiment":"positive","narrative":"Cream Finance DeFi借贷协议，涨幅+65%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol PNTUSDT --tag '{"sentiment":"positive","narrative":"pNetwork跨链基础设施，涨幅+45%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol EPICUSDT --tag '{"sentiment":"positive","narrative":"Epic Cash隐私币叙事，涨幅+42%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol PONDUSDT --tag '{"sentiment":"positive","narrative":"Marlin DePin去中心化网络，涨幅+36%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol WLDUSDT --tag '{"sentiment":"positive","narrative":"Worldcoin AI+身份Layer2，涨幅+21%成交量放量","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol KDAUSDT --tag '{"sentiment":"positive","narrative":"Kadena Layer1公链，涨幅+17.6%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol TONUSDT --tag '{"sentiment":"positive","narrative":"Toncoin Telegram生态Layer1，涨幅+16.8%成交量8655万","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol JTOUSDT --tag '{"sentiment":"positive","narrative":"Jito Solana生态流动性质押，涨幅+16.7%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol UTKUSDT --tag '{"sentiment":"positive","narrative":"Utrust加密支付解决方案，涨幅+16.2%","alert_level":"info"}'

# TOP11-30 有清晰叙事的币
python3 tools/enrich_coin.py --source A7 --symbol PORTALUSDT --tag '{"sentiment":"positive","narrative":"Portal GameFi跨链游戏平台，涨幅+14.7%成交量1.1亿","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol RIFUSDT --tag '{"sentiment":"positive","narrative":"RIF BTC生态基础设施，涨幅+13.7%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol ICPUSDT --tag '{"sentiment":"positive","narrative":"Internet Computer Layer1云计算公链，涨幅+12.3%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol WAVESUSDT --tag '{"sentiment":"positive","narrative":"Waves Layer1公链DeFi生态，涨幅+12%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol NEARUSDT --tag '{"sentiment":"positive","narrative":"NEAR Protocol Layer1公链，涨幅+11.6%成交量1.07亿","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol APEUSDT --tag '{"sentiment":"positive","narrative":"ApeCoin Meme+NFT生态，涨幅+11.6%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol AIGENSYNUSDT --tag '{"sentiment":"positive","narrative":"AIGENSYN AI叙事加密货币，涨幅+10.5%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol RONINUSDT --tag '{"sentiment":"positive","narrative":"Ronin GameFi侧链，涨幅+10.3%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol BERAUSDT --tag '{"sentiment":"positive","narrative":"Berachain Layer1流动性证明共识，涨幅+9.7%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol YGGUSDT --tag '{"sentiment":"positive","narrative":"Yield Guild Games GameFi公会，涨幅+9.5%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol EULUSDT --tag '{"sentiment":"positive","narrative":"Euler Finance DeFi借贷协议，涨幅+9.5%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol SYNUSDT --tag '{"sentiment":"positive","narrative":"Synapse跨链桥基础设施，涨幅+11.6%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol WUSDT --tag '{"sentiment":"positive","narrative":"Wormhole跨链互操作协议，涨幅+13%","alert_level":"info"}'
python3 tools/enrich_coin.py --source A7 --symbol CLVUSDT --tag '{"sentiment":"positive","narrative":"Clover Finance 波卡生态DeFi，涨幅+14%","alert_level":"info"}'

echo "✅ A7涨幅榜批量打标完成"
