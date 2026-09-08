#!/usr/bin/env python3
"""
动量雷达 v1.0 — 扫描谁在涨，不分析为什么不能涨

做什么：
  每30分钟，从Binance拉全市场24hr ticker，
  找出正在放量上涨的币（成交量>$1M + 涨+5%~+30%），
  按"动量质量"排序输出。

不做什么：
  - 不做RSI分析（涨的币RSI自然高，扣分没意义）
  - 不做叙事分析（涨就是最好的叙事）
  - 不做A2风格的五因子评分（那是找"便宜"不是找"在涨"）

输出：shared/momentum_signals.md
"""

import json
import os
import sys
from datetime import datetime

# ─── 配置 ───
MIN_VOLUME = 500_000         # 最低成交量 $500K（放低门槛，捕捉启动初期信号）
MIN_CHG = 3.0                # 最低涨幅 +3%（降一点，抓住刚启动的）
MAX_CHG = 30.0               # 最高涨幅 +30%（再高追不到了）
MIN_PRICE = 0.001            # 最低价格
MAX_CANDIDATES = 25          # 输出最多25个（老李要二十几个候选）

STABLECOINS = {"USDT", "BUSD", "DAI", "USDC", "FDUSD", "TUSD", "FRAX", "USTC", "PAXG", "XAUT", "EUR", "GBP"}
LEVERAGED_KW = {"UP", "DOWN", "BULL", "BEAR", "LONG", "SHORT", "2L", "2S", "3L", "3S", "5L", "5S"}

SOCKS5_PROXY = "socks5://127.0.0.1:1080"

# ─── 获取数据 ───

def fetch_ticker():
    """通过curl+SOCKS5代理获取Binance全市场24hr数据"""
    import subprocess
    
    url = "https://api.binance.com/api/v3/ticker/24hr"
    cmd = [
        "curl", "--socks5-hostname", "127.0.0.1:1080",
        "-s", "--max-time", "25",
        url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"❌ curl退出码: {result.returncode}", file=sys.stderr)
            return None
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print(f"❌ curl超时 (25s)", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ 获取数据失败: {e}", file=sys.stderr)
        return None

def is_valid(symbol, price, volume, change):
    """检查币种是否值得关注"""
    # 必须是USDT交易对
    if not symbol.endswith("USDT"):
        return False
    base = symbol.replace("USDT", "")
    
    # 排除稳定币/法币
    if base in STABLECOINS:
        return False
    
    # 排除杠杆代币
    for kw in LEVERAGED_KW:
        if kw in base.upper():
            return False
    
    # 硬条件
    if volume < MIN_VOLUME:
        return False
    if change < MIN_CHG or change > MAX_CHG:
        return False
    if price <= MIN_PRICE:
        return False
    
    return True

def calc_momentum_score(chg, volume):
    """
    动量质量分 (0-100)
    不是看"这个币安不安全"，是看"这个上涨质量高不高"
    """
    # 涨幅分 (40%)
    if chg >= 20:
        chg_score = 60    # 涨太多，可能接近尾声
    elif chg >= 12:
        chg_score = 90    # 强动量但还有空间
    elif chg >= 8:
        chg_score = 100   # 黄金区间
    else:
        chg_score = 80    # 刚启动
    
    # 成交量分 (60%) - 量大 = 真实资金
    if volume >= 100_000_000:
        vol_score = 100
    elif volume >= 50_000_000:
        vol_score = 90
    elif volume >= 20_000_000:
        vol_score = 80
    elif volume >= 10_000_000:
        vol_score = 70
    elif volume >= 5_000_000:
        vol_score = 60
    else:
        vol_score = 50
    
    total = chg_score * 0.4 + vol_score * 0.6
    return round(total, 1)

def get_top_changers(all_data):
    """全量数据中找涨幅前N的币（不看动量质量）"""
    candidates = []
    for d in all_data:
        try:
            symbol = d["symbol"]
            price = float(d["lastPrice"])
            volume = float(d["quoteVolume"])
            change = float(d["priceChangePercent"])
            high = float(d["highPrice"])
            low = float(d["lowPrice"])
            
            if not is_valid(symbol, price, volume, change):
                continue
            
            # 检查是不是暴跌反弹：从低点拉了50%+上来
            if low > 0 and price > 0:
                bounce_pct = (price - low) / low * 100
                if bounce_pct > 50:  # 从低点拉了50%以上
                    continue  # 暴跌反弹，不要
            
            score = calc_momentum_score(change, volume)
            candidates.append({
                "symbol": symbol.replace("USDT", ""),
                "change_24h": round(change, 2),
                "volume_24h": round(volume, 0),
                "price": round(price, 8),
                "score": score,
                "high_24h": round(high, 8),
                "low_24h": round(low, 8),
            })
        except (KeyError, ValueError, TypeError):
            continue
    
    # 按动量质量分排序
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates

def get_top_volume_gainers(all_data):
    """按涨幅排序的原始榜单"""
    candidates = []
    for d in all_data:
        try:
            symbol = d["symbol"]
            price = float(d["lastPrice"])
            volume = float(d["quoteVolume"])
            change = float(d["priceChangePercent"])
            high = float(d["highPrice"])
            low = float(d["lowPrice"])
            
            if not is_valid(symbol, price, volume, change):
                continue
            
            # 检查暴跌反弹
            if low > 0 and price > 0:
                bounce_pct = (price - low) / low * 100
                if bounce_pct > 50:
                    continue
            
            candidates.append({
                "symbol": symbol.replace("USDT", ""),
                "change_24h": round(change, 2),
                "volume_24h": round(volume, 0),
                "price": round(price, 8),
                "high_24h": round(high, 8),
                "low_24h": round(low, 8),
                "momentum_score": calc_momentum_score(change, volume),
            })
        except (KeyError, ValueError, TypeError):
            continue
    
    # 按涨幅排序
    candidates.sort(key=lambda c: c["change_24h"], reverse=True)
    return candidates

def get_btc_state(all_data):
    """从全量数据中提取BTC状态"""
    for d in all_data:
        if d["symbol"] == "BTCUSDT":
            return {
                "price": float(d["lastPrice"]),
                "change_24h": float(d["priceChangePercent"]),
                "volume": float(d["quoteVolume"]),
                "high": float(d["highPrice"]),
                "low": float(d["lowPrice"]),
            }
    return None

# ─── 主流程 ───

def main():
    # 工作目录
    base_dir = "/Users/lidaosong/zq_web4_trading_system"
    os.chdir(base_dir)
    
    print(f"🔍 动量雷达扫描开始... [{datetime.now().strftime('%m-%d %H:%M')}]")
    
    # 获取数据
    all_data = fetch_ticker()
    if not all_data:
        print("❌ 无法获取Binance数据，退出")
        sys.exit(1)
    
    print(f"✅ 获取 {len(all_data)} 个交易对数据")
    
    # BTC状态
    btc = get_btc_state(all_data)
    if btc:
        direction = "↑" if btc["change_24h"] > 0 else "↓"
        print(f"📊 BTC: ${btc['price']:,.2f} ({btc['change_24h']:+.2f}%) {direction}")
    
    # 按动量质量排序（优先）
    momentum_candidates = get_top_changers(all_data)
    top_momentum = momentum_candidates[:MAX_CANDIDATES]
    
    # 按涨幅排序（供参考）
    gainer_candidates = get_top_volume_gainers(all_data)
    top_gainers = gainer_candidates[:MAX_CANDIDATES]
    
    print(f"🏆 发现 {len(momentum_candidates)} 个动量候选")
    
    # ─── 写入输出文件 ───
    now = datetime.now().strftime("%Y-%m-%d %H:%M BJT")
    
    lines = []
    lines.append(f"# 📡 动量雷达信号 — {now}")
    lines.append("")
    
    # BTC状态
    if btc:
        lines.append(f"## 大盘背景")
        lines.append(f"| BTC | 24h | 方向 | 适合做多？ |")
        lines.append(f"|:----|:---:|:----:|:----------:|")
        dir_label = "🟢适合" if btc["change_24h"] > -3 else "🔴谨慎"
        lines.append(f"| ${btc['price']:,.0f} | {btc['change_24h']:+.2f}% | {'↑' if btc['change_24h']>0 else '↓'} | {dir_label} |")
        lines.append("")
    
    # 动量质量TOP 20
    lines.append(f"## 🏆 动量质量TOP {min(20, len(top_momentum))}")
    lines.append("| 排名 | 币种 | 涨幅% | 成交量 | 价格 | 质量分 |")
    lines.append("|:----:|:----|:----:|:------:|:-----:|:------:|")
    for i, c in enumerate(top_momentum[:20]):
        rank_icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"#{i+1}"
        vol_str = f"${c['volume_24h']:,.0f}"
        price_str = f"${c['price']:.6f}" if c['price'] < 1 else f"${c['price']:.4f}"
        lines.append(f"| {rank_icon} | {c['symbol']} | **+{c['change_24h']:.2f}%** | {vol_str} | {price_str} | **{c['score']}** |")
    lines.append("")
    
    # 涨幅榜TOP 20（补充，防止动量质量漏掉纯涨幅大的）
    lines.append(f"## ⚡ 涨幅榜TOP {min(20, len(top_gainers))}")
    lines.append("| 排名 | 币种 | 涨幅% | 成交量 | 价格 | 质量分 |")
    lines.append("|:----:|:----|:----:|:------:|:-----:|:------:|")
    for i, c in enumerate(top_gainers[:20]):
        vol_str = f"${c['volume_24h']:,.0f}"
        price_str = f"${c['price']:.6f}" if c['price'] < 1 else f"${c['price']:.4f}"
        lines.append(f"| #{i+1} | {c['symbol']} | **+{c['change_24h']:.2f}%** | {vol_str} | {price_str} | **{c['momentum_score']}** |")
    lines.append("")
    
    # 最佳买入候选（质量分最高的前3个，单独推荐）
    lines.append(f"## 🎯 今日最佳动量候选")
    lines.append("")
    for i, c in enumerate(top_momentum[:3]):
        lines.append(f"### {'🥇' if i==0 else '🥈' if i==1 else '🥉'} {c['symbol']}")
        lines.append(f"- 24h涨幅: **+{c['change_24h']:.2f}%**")
        lines.append(f"- 成交量: **${c['volume_24h']:,.0f}**")
        lines.append(f"- 当前价: **${c['price']:.6f}**" if c['price'] < 1 else f"- 当前价: **${c['price']:.4f}**")
        lines.append(f"- 24h区间: ${c['low_24h']:.6f} ~ ${c['high_24h']:.6f}")
        
        # 入场建议
        pullback = round(c['price'] * 0.95, 8)  # 回调5%入场
        stoploss = round(c['price'] * 0.92, 8)  # 止损8%
        target = round(c['price'] * 1.10, 8)     # 止盈10%
        
        lines.append(f"- 建议入场: **${pullback:.6f}**（回调5%）" if pullback < 1 else f"- 建议入场: **${pullback:.4f}**（回调5%）")
        lines.append(f"- 止损: **${stoploss:.6f}**（-8%）" if stoploss < 1 else f"- 止损: **${stoploss:.4f}**（-8%）")
        lines.append(f"- 止盈: **${target:.6f}**（+10%）" if target < 1 else f"- 止盈: **${target:.4f}**（+10%）")
        lines.append("")
    
    # 全量候选
    if len(momentum_candidates) > 10:
        lines.append(f"<details>")
        lines.append(f"<summary>📋 全量候选（共{len(momentum_candidates)}个）</summary><br>")
        lines.append("")
        lines.append("| 币种 | 涨幅% | 成交量 | 价格 | 质量分 |")
        lines.append("|:----|:----:|:------:|:-----:|:------:|")
        for c in momentum_candidates:
            vol_str = f"${c['volume_24h']:,.0f}"
            price_str = f"${c['price']:.6f}" if c['price'] < 1 else f"${c['price']:.4f}"
            lines.append(f"| {c['symbol']} | +{c['change_24h']:.2f}% | {vol_str} | {price_str} | {c['score']} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    
    lines.append(f"---")
    lines.append(f"*扫描时间: {now} | 数据源: Binance API via SOCKS5*")
    lines.append(f"*生成: tools/momentum_radar.py*")
    
    output = "\n".join(lines)
    
    # 写入文件
    output_path = os.path.join(base_dir, "shared", "momentum_signals.md")
    with open(output_path, "w") as f:
        f.write(output)
    
    print(f"✅ 写入 {output_path}")
    print(f"📊 动量候选 {len(momentum_candidates)} 个 | 涨幅候选 {len(gainer_candidates)} 个")
    
    # 输出TOP 3摘要到stdout
    print(f"\n🎯 TOP 3 动量候选:")
    for i, c in enumerate(top_momentum[:3]):
        print(f"  {i+1}. {c['symbol']}: +{c['change_24h']:.2f}% | Vol: ${c['volume_24h']:,.0f} | Score: {c['score']}")

if __name__ == "__main__":
    main()
