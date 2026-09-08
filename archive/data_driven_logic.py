import hmac
import hashlib
import time
import requests
import json
from datetime import datetime

# 全网数据源
DATA_SOURCES = {
    "LONG_SHORT_RATIO": "https://fapi.binance.com/fapi/v1/globalLongShortAccountRatio", # 多空比
    "LIQUIDATION": "https://fapi.binance.com/fapi/v1/allForceOrders", # 强平监控
    "FUNDING_RATE": "https://fapi.binance.com/fapi/v1/fundingRate"    # 资金费率
}

AUTH_PATH = "/Users/lidaosong/zq_web4_trading_system/config/auth.json"

def get_auth():
    with open(AUTH_PATH, 'r') as f:
        data = json.load(f)
        return data['binance']['api_key'], data['binance']['api_secret']

def get_global_sentiment(symbol):
    """
    抓取全网实时数据：多空比、强平、资金费率
    """
    try:
        # 1. 多空比 (反映散户/大户博弈)
        ratio_resp = requests.get(f"https://fapi.binance.com/fapi/v1/globalLongShortAccountRatio?symbol={symbol}USDT&period=5m&limit=1").json()
        ratio = float(ratio_resp[0]['longShortRatio']) if ratio_resp else 1.0
        
        # 2. 资金费率 (反映溢价)
        funding_resp = requests.get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}USDT&limit=1").json()
        funding = float(funding_resp[0]['fundingRate']) if funding_resp else 0.0
        
        return ratio, funding
    except:
        return 1.0, 0.0

def logic_engine():
    ak, sk = get_auth()
    # 策略池
    COINS = ['MOVR', 'APE', 'ENA', 'PEPE', 'SOL', 'DOGE']
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🧠 数据驱动决策引擎逻辑自检: ")
    
    for coin in COINS:
        symbol = f"{coin}USDT"
        
        # 1. 价格 & RSI (基础面)
        # 2. 全网多空比 & 资金费率 (情感面 - 核心逻辑)
        ls_ratio, funding = get_global_sentiment(coin)
        
        msg = f"  {coin:<5} | 多空比: {ls_ratio:.2f} | 资金费: {funding:.6f}"
        
        # 逻辑：如果 RSI 低位 且 多空比 > 1.2 (有人在抄底) 且 资金费为正 -> 考虑介入
        # 逻辑：如果 多空比骤降 且 价格跌破支点 -> 强制止损
        print(msg)

if __name__ == "__main__":
    logic_engine()
