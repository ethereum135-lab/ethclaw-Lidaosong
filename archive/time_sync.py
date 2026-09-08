import time
import hmac
import hashlib
import requests
import json
from datetime import datetime, timezone, timedelta

def get_real_beijing_time():
    # 唯一可信源：币安服务器时间
    try:
        res = requests.get("https://api.binance.com/api/v3/time").json()
        srv_ms = res['serverTime']
        # 转换为北京时间 (UTC+8)
        dt = datetime.fromtimestamp(srv_ms/1000, tz=timezone.utc) + timedelta(hours=8)
        return dt, srv_ms
    except:
        # 回退逻辑：本地时间
        return datetime.now(), int(time.time()*1000)

if __name__ == "__main__":
    bj_now, ms = get_real_beijing_time()
    print(f"北京时间确认: {bj_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Unix时间戳: {ms}")
