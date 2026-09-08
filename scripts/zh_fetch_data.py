import urllib.request, json

# Top gainers from CoinGecko
url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=50&page=1&sparkline=false"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read())

# Sort by price change percent descending
sorted_data = sorted(data, key=lambda x: x.get('price_change_percentage_24h', 0), reverse=True)

print("=== CoinGecko Top 10 Gainers (24h) ===")
for coin in sorted_data[:10]:
    sym = coin['symbol'].upper()
    chg = coin.get('price_change_percentage_24h', 0)
    vol = coin.get('total_volume', 0)
    mcap = coin.get('market_cap', 0)
    print(f"{sym:8s} ${coin['current_price']:<12.4f} {chg:>+7.2f}% vol:${vol:<10.0f} mcap:${mcap:<12.0f}")

# Global data
url2 = "https://api.coingecko.com/api/v3/global"
req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
resp2 = urllib.request.urlopen(req2, timeout=15)
global_data = json.loads(resp2.read())
g = global_data['data']
print(f"\n=== Market Overview ===")
print(f"Total MC: ${g['total_market_cap']['usd']:,.0f}")
print(f"24h Vol: ${g['total_volume']['usd']:,.0f}")
print(f"BTC Dom: {g['market_cap_percentage']['btc']:.1f}%")
print(f"ETH Dom: {g['market_cap_percentage'].get('eth', 0):.1f}%")

# Also get BTC price
btc_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true"
req3 = urllib.request.Request(btc_url, headers={'User-Agent': 'Mozilla/5.0'})
resp3 = urllib.request.urlopen(req3, timeout=15)
btc_data = json.loads(resp3.read())
print(f"\nBTC: ${btc_data['bitcoin']['usd']:,.0f} (24h: {btc_data['bitcoin'].get('usd_24h_change', 0):+.2f}%)")
print(f"ETH: ${btc_data['ethereum']['usd']:,.0f} (24h: {btc_data['ethereum'].get('usd_24h_change', 0):+.2f}%)")
