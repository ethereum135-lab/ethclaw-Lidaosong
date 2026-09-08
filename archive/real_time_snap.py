import json, time
from binance.client import Client
def snap():
    f = open('/home/ubuntu/zq_web4_trading_system/config/auth.json')
    c = json.load(f)
    client = Client(c['api_key'], c['secret_key'])
    # 获取全币种余额并写入本地缓存，供 ZQ 大脑读取
    balances = client.get_account()['balances']
    live = [b for b in balances if float(b['free']) > 0 or float(b['locked']) > 0]
    with open('/home/ubuntu/zq_web4_trading_system/config/live_balances.json', 'w') as out:
        json.dump(live, out)
    print(f"[{time.ctime()}] 🛡️ 全资产快照已刷新。")
if __name__ == "__main__":
    while True:
        try: snap()
        except: pass
        time.sleep(60) # 每一分钟，服务器自己查一次账
