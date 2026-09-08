#!/usr/bin/env python3
"""A1 数据采集管道 — 一键版
用法: python3 tools/a1_data_pipeline.py
职责: 
  1. python3 tools/aws_data_fetch.py → 采集所有AWS数据
  2. 读取 snapshot → 生成 data_feed.md + 报告
  3. 写入 profiles/a1-data/output/
"""

import json, os, subprocess, sys, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SNAPSHOT = BASE / 'data' / 'aws_snapshot.json'
A1_OUTPUT = BASE / 'profiles' / 'a1-data' / 'output'
DATA_FEED = A1_OUTPUT / 'data_feed.md'

TZ_BJT = datetime.timezone(datetime.timedelta(hours=8))

def log(msg):
    ts = datetime.datetime.now(TZ_BJT).strftime('%Y-%m-%d %H:%M BJT')
    print(f'[{ts}] {msg}')

def run_aws_fetch():
    """Step 1: Run AWS data fetch"""
    log('🚀 运行 aws_data_fetch.py ...')
    result = subprocess.run(
        [sys.executable, 'tools/aws_data_fetch.py'],
        cwd=BASE, capture_output=True, text=True, timeout=120
    )
    for line in result.stdout.strip().split('\n'):
        log(f'  {line.strip()}')
    if result.returncode != 0:
        log(f'⚠️  aws_data_fetch 返回码 {result.returncode}')
        log(f'  stderr: {result.stderr.strip()[:500]}')
        return False
    
    if not SNAPSHOT.exists():
        log(f'❌ {SNAPSHOT} 未生成')
        return False
    
    size = SNAPSHOT.stat().st_size
    log(f'✅ snapshot 已保存 ({size} bytes)')
    return True

def read_snapshot(data):
    """从snapshot提取结构化数据"""
    # F&G
    fg_val = data.get('fg_index', 'N/A')
    fg_label = data.get('fg_classification', 'N/A')
    
    # BTC/ETH价格 — 从binance_top200找
    top50 = data.get('binance_top200', data.get('binance_top50', []))
    btc_price = 'N/A'
    eth_price = 'N/A'
    for coin in top50:
        sym = coin.get('symbol', '').upper()
        price = coin.get('price', 'N/A')
        if 'BTCUSDT' == sym:
            btc_price = price
        elif 'ETHUSDT' == sym:
            eth_price = price
    
    # 资金费率 Top15 (按费率绝对值排序)
    fr_dict = data.get('funding_rates', {})
    fr_list = []
    for sym, info in fr_dict.items():
        rate_str = info.get('rate', '0')
        try:
            rate_pct = float(rate_str) * 100
        except:
            rate_pct = 0
        fr_list.append({
            'symbol': sym,
            'rate': round(rate_pct, 4),
            'rate_raw': rate_str,
        })
    # 按费率绝对值排序，取前15
    fr_list.sort(key=lambda x: abs(x['rate']), reverse=True)
    fr_top = fr_list[:15]
    
    # Trending
    trending_raw = data.get('coingecko_trending', [])
    trending_names = [t.get('name', 'N/A') for t in trending_raw[:5]]
    
    # 全球数据
    global_data = data.get('global', {})
    dominance = global_data.get('btc_dominance', 'N/A')
    total_mcap = global_data.get('total_mcap_usd', 'N/A')
    total_vol = global_data.get('total_vol_usd', 'N/A')
    
    # 格式化市值
    try:
        mcap_fmt = f'${float(total_mcap):.2f}'
    except:
        mcap_fmt = f'${total_mcap}'
    
    return {
        'fg_value': fg_val,
        'fg_label': fg_label,
        'btc_price': btc_price,
        'eth_price': eth_price,
        'dominance': dominance,
        'total_mcap': mcap_fmt,
        'total_vol': total_vol,
        'funding_rates': fr_top,
        'trending': trending_names,
        'data_quality': data.get('data_quality', 'N/A'),
        'errors': data.get('errors', []),
    }

def format_rate(rate_val):
    """格式化费率显示"""
    if rate_val == 'N/A' or rate_val is None:
        return 'N/A', 'neutral'
    try:
        r = float(rate_val)
        if r > 0.005:
            return f'{r:.4f}', 'long_pays_short'
        elif r < -0.005:
            return f'{r:.4f}', 'short_pays_long'
        else:
            return f'{r:.4f}', 'neutral'
    except:
        return 'N/A', 'neutral'

def write_data_feed(stats):
    """写入 data_feed.md 结构化数据"""
    now = datetime.datetime.now(TZ_BJT)
    
    # market judgment
    try:
        fg_int = int(stats['fg_value'])
        if fg_int < 40:
            judgment = 'fear'
        elif fg_int < 60:
            judgment = 'neutral'
        else:
            judgment = 'greed'
    except:
        judgment = 'unknown'
    
    lines = [
        f'# A1 DATA FEED — {now.strftime("%Y-%m-%d %H:%M BJT")}',
        '',
        '## MACRO',
        f'- fg_value: {stats["fg_value"]}',
        f'- fg_label: {stats["fg_label"]}',
        f'- btc_price: ${stats["btc_price"]}',
        f'- eth_price: ${stats["eth_price"]}',
        f'- btc_dominance: {stats["dominance"]}%',
        f'- market_judgment: {judgment}',
        '',
        '## FUNDING_RATES (Top10)',
        '| symbol | rate | direction |',
        '|:-------|:----:|:---------:|',
    ]
    
    if stats['funding_rates']:
        for r in stats['funding_rates'][:10]:
            rate_display, direction = format_rate(r['rate_raw'])
            lines.append(f'| {r["symbol"]} | {rate_display}% | {direction} |')
    else:
        lines.append('| N/A | N/A | N/A |')
    
    lines.append('')
    lines.append('## TRENDING (Top5)')
    if stats['trending']:
        for i, name in enumerate(stats['trending'], 1):
            lines.append(f'{i}. {name}')
    else:
        for i in range(1, 6):
            lines.append(f'{i}. N/A')
    
    lines.append('')
    lines.append('## MISSING')
    lines.append('- smart_wallet: not_connected')
    lines.append('- onchain: not_connected')
    lines.append('- news: not_connected')
    lines.append('')
    
    content = '\n'.join(lines)
    with open(DATA_FEED, 'w') as f:
        f.write(content)
    log(f'✅ 已写入 data_feed.md ({len(content)} chars)')

def write_full_report(stats):
    """写入人类可读报告"""
    now = datetime.datetime.now(TZ_BJT)
    date_str = now.strftime('%Y-%m-%d')
    report_path = A1_OUTPUT / f'{date_str}.md'
    
    lines = [
        f'# A1 数据采集报告 — {date_str}',
        f'采集时间：{now.strftime("%H:%M BJT")}',
        f'数据来源：AWS→Binance API + AWS→CoinGecko API (15.134.211.154) | Alternative.me',
        '',
        '---',
        '',
        '## ① 市场情绪',
        f'- F&G指数：{stats["fg_value"]}/100 — {stats["fg_label"]}',
        f'- BTC Dominance：{stats["dominance"]}%',
        f'- 总市值：{stats["total_mcap"]}',
        f'- BTC价格：${stats["btc_price"]}',
        f'- ETH价格：${stats["eth_price"]}',
        '',
        '## ② 资金费率（Top10）',
        '| 币种 | 费率 | 方向 |',
        '|:----|:----:|:----:|',
    ]
    
    if stats['funding_rates']:
        for r in stats['funding_rates'][:10]:
            rate_display, direction = format_rate(r['rate_raw'])
            dir_cn = '多付空' if 'long_pays_short' in direction else '空付多' if 'short_pays_long' in direction else '中性'
            lines.append(f'| {r["symbol"]} | {rate_display}% | {dir_cn} |')
    else:
        lines.append('| N/A | N/A | N/A |')
    
    lines.append('')
    lines.append('## ③ 社交热度')
    if stats['trending']:
        lines.append(f'Trending：{"、".join(stats["trending"])}')
    else:
        lines.append('（无数据）')
    
    lines.append('')
    lines.append('## ④ 聪明钱包 — 待接入')
    lines.append('## ⑤ 链上数据 — 待接入')
    lines.append('## ⑥ 新闻舆情 — 待接入')
    
    lines.append('')
    lines.append('---')
    lines.append(f'*采集时间：{now.strftime("%Y-%m-%d %H:%M BJT")}*')
    lines.append(f'*数据通道：AWS SSH 15.134.211.154 → Binance/CoinGecko*')
    lines.append(f'*数据质量：{stats["data_quality"]}*')
    if stats['errors']:
        lines.append(f'*错误：{", ".join(stats["errors"][:3])}*')
    lines.append('')
    
    content = '\n'.join(lines)
    with open(report_path, 'w') as f:
        f.write(content)
    log(f'✅ 已写入 {date_str}.md ({len(content)} chars)')

def main():
    log('=' * 50)
    log('A1 数据采集管道 启动')
    
    A1_OUTPUT.mkdir(parents=True, exist_ok=True)
    
    if not run_aws_fetch():
        log('❌ AWS数据采集失败，尝试本地F&G...')
        try:
            import requests
            fg_resp = requests.get('https://api.alternative.me/fng/', timeout=10).json()
            snapshot_data = {
                'fg_index': fg_resp['data'][0]['value'],
                'fg_classification': fg_resp['data'][0]['value_classification'],
                'binance_top200': [],
                'funding_rates': {},
                'coingecko_trending': [],
                'global': {},
                'data_quality': 'partial_fg_only',
                'errors': ['AWS数据采集失败'],
            }
            log(f'✅ F&G: {fg_resp["data"][0]["value"]}/100 — {fg_resp["data"][0]["value_classification"]}')
        except Exception as e:
            log(f'❌ F&G也失败: {e}')
            return False
    else:
        with open(SNAPSHOT) as f:
            snapshot_data = json.load(f)
        log(f'✅ 成功读取snapshot，{len(json.dumps(snapshot_data))} chars')
    
    stats = read_snapshot(snapshot_data)
    
    log(f'   F&G: {stats["fg_value"]}/100 — {stats["fg_label"]}')
    log(f'   BTC: ${stats["btc_price"]} | ETH: ${stats["eth_price"]}')
    log(f'   Trending: {stats["trending"]}')
    log(f'   费率采集: {len(stats["funding_rates"])}个币')
    
    write_data_feed(stats)
    write_full_report(stats)
    
    log('✅ A1 数据采集管道完成')

if __name__ == '__main__':
    main()
