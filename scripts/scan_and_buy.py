import json
import requests
import pandas as pd
from binance.client import Client

def execute():
    try:
        with open('/Users/lidaosong/zq_web4_trading_system/config/auth.json') as f:
            auth = json.load(f)
        client = Client(auth['binance']['api_key'], auth['binance']['api_secret'])
        
        # 1. Price/Volume check
        tickers = client.get_ticker()
        df = pd.DataFrame(tickers)
        df['quoteVolume'] = df['quoteVolume'].astype(float)
        df = df[df['symbol'].str.endswith('USDT') & ~df['symbol'].isin(['BTCUSDT', 'ETHUSDT'])]
        top_50 = df.sort_values('quoteVolume', ascending=False).head(50)['symbol'].tolist()
        
        balance = float(client.get_asset_balance(asset='USDT')['free'])
        if balance < 10:
            return "STATUS: Scanning 50 coins, insufficient USDT balance (<10)"

        for symbol in top_50:
            try:
                klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1MINUTE, limit=30)
                closes = pd.Series([float(k[4]) for k in klines])
                
                # Simple RSI
                delta = closes.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rsi = 100 - (100 / (1 + gain/loss)).iloc[-1]
                
                drop = (closes.iloc[-2] - closes.iloc[-1]) / closes.iloc[-2]
                
                if drop > 0.01 and rsi < 35:
                    order = client.order_market_buy(symbol=symbol, quoteOrderQty=round(balance * 0.98, 2))
                    return f"ACTION: Bought {symbol} at {closes.iloc[-1]}"
            except:
                continue
        return "STATUS: Scanning 50 coins, no signal"
    except Exception as e:
        return f"ERROR: {str(e)}"

if __name__ == '__main__':
    print(execute())
