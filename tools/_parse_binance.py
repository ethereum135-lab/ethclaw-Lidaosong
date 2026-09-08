import json,sys
data=json.load(sys.stdin)
usdt_pairs = [x for x in data if x['symbol'].endswith('USDT')]
stablecoins = ['USDCUSDT','BUSDUSDT','DAIUSDT','FDUSDUSDT','TUSDUSDT','USDPUSDT','GUSDUSDT','PAXGUSDT','EURUSDT','GBPUSDT']
usdt_pairs = [x for x in usdt_pairs if x['symbol'] not in stablecoins and 'UPUSDT' not in x['symbol'] and 'DOWNUSDT' not in x['symbol'] and 'BULL' not in x['symbol'] and 'BEAR' not in x['symbol'] and 'LUNA' not in x['symbol']]
sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['priceChangePercent']), reverse=True)
top10 = sorted_pairs[:10]
print('=== 币安24h涨幅TOP10 ===')
for i,p in enumerate(top10,1):
    sym=p['symbol']
    chg=p['priceChangePercent']
    vol=float(p['quoteVolume'])
    price=p['lastPrice']
    print(f'{i}. {sym}: +{chg}%  ${price}  vol:{vol:.0f}')
