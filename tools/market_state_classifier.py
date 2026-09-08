#!/usr/bin/env python3
"""
市场状态分类器 v1.0 — 开盘后判断今天是什么市场
===========================================
在 NAVIGATION.md §三(FNG风控旋钮)之上再加一层市场状态层。
FNG决定"市场情绪"，市场状态决定"今天怎么交易"。

运行: 09:15 BJT（开盘30分钟稳定后） + 13:00 BJT（下午重估）

输出: data/market_state.json — 所有Agent读取

分类:
  - trend_up    趋势向上日 → 正常做，4仓全开
  - trend_down  趋势向下日 → 只平不建新仓，减到2仓
  - range       震荡日     → 谨慎，减仓，快进快出
  - low_vol     低活跃日   → 只平不建，等变盘
  - explosive   爆发日     → 全仓冲锋，4仓满仓

判断方法(3个独立维度交叉验证):
  1. top50均值涨跌 + 涨跌占比(广度)
  2. BTC方向 + 幅度
  3. 成交量对比24h(量是真是假)
"""

import json, subprocess, sys, os
from datetime import datetime

BASE = os.path.expanduser("~/zq_web4_trading_system")
OUTPUT = os.path.join(BASE, "data/market_state.json")
MIN_VOLUME = 300_000


def api_get(url):
    r = subprocess.run(
        ['curl', '-s', '--connect-timeout', '10', '--max-time', '25',
         '--socks5-hostname', '127.0.0.1:1080', url],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0 or not r.stdout:
        return None
    return json.loads(r.stdout)


def check_state():
    now = datetime.now()
    print(f"=== 市场状态分类器 v1.0 === {now.strftime('%Y-%m-%d %H:%M')}")
    
    # 1. 拉BTC + ETH大盘
    btc = api_get('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT')
    eth = api_get('https://api.binance.com/api/v3/ticker/24hr?symbol=ETHUSDT')
    
    if not btc:
        print("❌ BTC API失败，跳过")
        return
        
    btc_price = float(btc['lastPrice'])
    btc_chg = float(btc['priceChangePercent'])
    btc_vol = float(btc['quoteVolume'])
    
    eth_price = float(eth['lastPrice']) if eth else 0
    eth_chg = float(eth['priceChangePercent']) if eth else 0
    
    # 2. 拉全市场，分析top50成交量币
    all_tickers = api_get('https://api.binance.com/api/v3/ticker/24hr')
    if not all_tickers:
        print("❌ 全市场API失败")
        return
    
    # 过滤USDT对
    usdt = []
    for t in all_tickers:
        sym = t.get('symbol', '')
        if not sym.endswith('USDT'):
            continue
        try:
            vol = float(t['quoteVolume'])
            chg = float(t['priceChangePercent'])
            price = float(t['lastPrice'])
        except:
            continue
        # 过滤稳定币、杠杆代币
        base = sym.replace('USDT', '').replace('1000', '')
        skips = ['UP','DOWN','BULL','BEAR','BUSD','USDC','DAI','FDUSD','USDP',
                 'EUR','GBP','AUD','BRL','TRY','ZAR','IDRT','USTC','USDD','SUSD']
        if any(k in base for k in skips):
            continue
        if vol < MIN_VOLUME:
            continue
        usdt.append({'sym': sym, 'vol': vol, 'chg': chg, 'price': price})
    
    # 取top50成交量
    usdt.sort(key=lambda x: -x['vol'])
    top50 = usdt[:50]
    
    if len(top50) < 10:
        print(f"❌ 有效数据不足({len(top50)}个)")
        return
    
    # 3. 分析维度
    avg_chg = sum(c['chg'] for c in top50) / len(top50)
    gainers = [c for c in top50 if c['chg'] >= 3]
    strong_gainers = [c for c in top50 if c['chg'] >= 5]
    decliners = [c for c in top50 if c['chg'] <= -3]
    flat = [c for c in top50 if -1 < c['chg'] < 1]
    
    gainer_pct = len(gainers) / len(top50) * 100
    strong_pct = len(strong_gainers) / len(top50) * 100
    decliner_pct = len(decliners) / len(top50) * 100
    flat_pct = len(flat) / len(top50) * 100
    
    best = max(c['chg'] for c in top50)
    worst = min(c['chg'] for c in top50)
    spread = best - worst
    
    # 成交量健康度
    top50_vol_total = sum(c['vol'] for c in top50)
    # 用于和24h前的自身对比(暂略)
    
    # 4. 分类决策树
    reasons = []
    state = "unknown"
    posture = "normal"
    max_positions = 4
    position_pct_mult = 1.0  # FNG仓位×这个系数
    
    # --- 先判断极端情况 ---
    
    # 爆发日: >30%的币涨3%+, 有>=5%的币
    if strong_pct >= 10 and avg_chg >= 3 and btc_chg >= 1:
        state = "explosive"
        posture = "aggressive"
        max_positions = 4
        position_pct_mult = 1.5  # 仓位放大50%
        reasons.append(f"爆发: {strong_pct:.0f}%币涨>5%, 均值+{avg_chg:.1f}%, BTC+{btc_chg:.1f}%")
    
    # 恐慌日: >20%的币跌3%+, BTC跌>3%
    elif decliner_pct >= 20 and btc_chg <= -3:
        state = "gap_down"
        posture = "survival"
        max_positions = 0  # 不平不开仓，只卖
        position_pct_mult = 0
        reasons.append(f"恐慌: {decliner_pct:.0f}%币跌, BTC{btc_chg:+.1f}%")
    
    # 趋势向上日: 均值>1%, 涨>跌, BTC涨
    elif avg_chg >= 1 and gainer_pct > decliner_pct + 10 and btc_chg >= 0:
        state = "trend_up"
        posture = "normal"
        max_positions = 4
        position_pct_mult = 1.0
        reasons.append(f"趋势向上: 均值+{avg_chg:.1f}%, {gainer_pct:.0f}%涨>{decliner_pct:.0f}%跌")
    
    # 趋势向下日: 均值<-1%, 跌>涨
    elif avg_chg <= -1 and decliner_pct > gainer_pct + 10:
        state = "trend_down"
        posture = "defensive"
        max_positions = 2
        position_pct_mult = 0.5
        reasons.append(f"趋势向下: 均值{avg_chg:.1f}%, {decliner_pct:.0f}%跌")
    
    # 震荡: 横盘多，涨跌都很散
    elif flat_pct >= 30 and abs(avg_chg) < 1.5:
        state = "range"
        posture = "cautious"
        max_positions = 3
        position_pct_mult = 0.7
        reasons.append(f"震荡: {flat_pct:.0f}%横盘, 均值{avg_chg:+.1f}%")
    
    # 低活跃: 涨跌很少，量异常
    elif flat_pct >= 40 and abs(avg_chg) < 1:
        state = "low_vol"
        posture = "wait"
        max_positions = 2
        position_pct_mult = 0.5
        reasons.append(f"低活跃: {flat_pct:.0f}%横盘, 少动")
    
    else:
        state = "range"
        posture = "cautious"
        max_positions = 3
        position_pct_mult = 0.7
        reasons.append(f"混合: 均值{avg_chg:+.1f}%, {gainer_pct:.0f}%涨/{decliner_pct:.0f}%跌")
    
    # 5. 输出
    result = {
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
        "state": state,
        "posture": posture,
        "max_positions": max_positions,
        "position_pct_mult": position_pct_mult,
        "reason": "; ".join(reasons),
        "metrics": {
            "btc_price": round(btc_price, 2),
            "btc_change_24h": round(btc_chg, 2),
            "eth_price": round(eth_price, 2),
            "eth_change_24h": round(eth_chg, 2),
            "top50_avg_change": round(avg_chg, 2),
            "top50_gainer_pct": round(gainer_pct, 1),
            "top50_strong_gainer_pct": round(strong_pct, 1),
            "top50_decliner_pct": round(decliner_pct, 1),
            "top50_flat_pct": round(flat_pct, 1),
            "top50_best_change": round(best, 2),
            "top50_worst_change": round(worst, 2),
            "top50_spread": round(spread, 2),
            "top50_vol_total": round(top50_vol_total, 0),
            "top50_count": len(top50),
        },
        "posture_action": {
            "trend_up": "🟢 正常交易，4仓满，追涨幅榜刚启动",
            "explosive": "🟢🟢 爆发日！积极建仓，仓位可放大1.5倍",
            "range": "🟡 震荡，减到3仓，快进快出，到+5%就止盈",
            "low_vol": "🟡 低活跃，减到2仓，只交易有量的币",
            "trend_down": "🔴 趋势向下，只平不建新仓",
            "gap_down": "🔴🔴 恐慌日，不开新仓，减仓到最低",
        }.get(state, "🟡 谨慎交易"),
    }
    
    json.dump(result, open(OUTPUT, 'w'), indent=2)
    
    # 6. 打印
    state_icons = {"explosive": "🔥", "trend_up": "📈", "range": "📊",
                   "low_vol": "💤", "trend_down": "📉", "gap_down": "💀"}
    icon = state_icons.get(state, "❓")
    
    print(f"\n{icon} 市场状态: {state.upper()} | 策略: {posture}")
    print(f"   原因: {result['reason']}")
    print(f"   最多仓位: {max_positions} | 仓位系数: {position_pct_mult}x")
    print(f"   BTC: ${btc_price:,.0f} ({btc_chg:+.2f}%) | ETH: ${eth_price:,.0f} ({eth_chg:+.2f}%)")
    print(f"   Top50均值: {avg_chg:+.2f}% | 涨>3%: {gainer_pct:.0f}% | 跌>3%: {decliner_pct:.0f}%")
    print(f"   说明: {result['posture_action']}")
    print(f"\n✅ 已写入 {OUTPUT}")


if __name__ == '__main__':
    check_state()
