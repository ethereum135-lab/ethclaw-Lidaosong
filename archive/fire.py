import sys
from binance.client import Client
import json

try:
    with open('/etc/zq_trading/auth.json', 'r') as f:
        auth = json.load(f)
    
    client = Client(auth['api_key'], auth['api_secret'])
    
    # 获取 APE 余额并卖出 20 个
    order = client.create_order(
        symbol='APEUSDT',
        side='SELL',
        type='MARKET',
        quantity=20
    )
    print(f'SUCCESS|{order["orderId"]}')
except Exception as e:
    print(f'ERROR|{str(e)}')

