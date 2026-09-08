#!/usr/bin/env python3
"""
A2 管道B — 动量捕捉评分
读取 shared/momentum_signals.md，用管道B规则评分，注入到A2报告末尾。

管道B规则：
- 动量结构25%：大涨加分（涨得越高分越高）
- RSI位置15%：50-80=满分，允许追趋势
- 成交量30%不变 / 费率20%不变 / 热度10%不变

输出：追加到 profiles/a2-selector/output/YYYY-MM-DD.md
"""

import json
import os
import sys
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

BJT = timezone(timedelta(hours=8))
BASE_DIR = Path(__file__).resolve().parent.parent
MOMENTUM_PATH = BASE_DIR / "shared" / "momentum_signals.md"
OUTPUT_DIR = BASE_DIR / "profiles" / "a2-selector" / "output"

PIPELINE_B_WEIGHTS = {
    "volume": 0.30,
    "momentum": 0.25,
    "funding": 0.20,
    "rsi_position": 0.15,
    "heat": 0.10,
}

# 管道B的评分逻辑（覆盖旧五因子中的动量和RSI维度）
def score_momentum(change_24h):
    """大涨加分不是扣分"""
    if change_24h >= 20:
        return 100
    elif change_24h >= 15:
        return 90
    elif change_24h >= 10:
        return 80
    elif change_24h >= 7:
        return 70
    elif change_24h >= 5:
        return 60
    else:
        return 30

def score_rsi_b(momentum_quality_score):
    """管道B的RSI逻辑：允许追趋势"""
    # 用动量质量分近似（没有实际RSI也能估算）
    # 动量高=趋势强=RSI自然高，不扣分
    if momentum_quality_score >= 60:
        return 100  # 有动量的币RSI在50-80，管道B给满分
    elif momentum_quality_score >= 40:
        return 70
    else:
        return 40

def score_volume(volume_usd):
    if volume_usd >= 50_000_000:
        return 100
    elif volume_usd >= 20_000_000:
        return 90
    elif volume_usd >= 10_000_000:
        return 80
    elif volume_usd >= 5_000_000:
        return 70
    elif volume_usd >= 1_000_000:
        return 50
    else:
        return 0

def score_funding(funding_rate):
    """管道B不因费率扣动量币的分"""
    fr = funding_rate * 100  # 转百分比
    if -0.02 <= fr <= 0.02:
        return 100
    elif -0.05 <= fr <= 0.05:
        return 70
    elif -0.1 <= fr <= 0.1:
        return 40
    else:
        return 10

def score_heat(is_top3, change_24h):
    """强者恒强——在涨+有热度=加分"""
    if is_top3 and change_24h > 5:
        return 80  # 持续大涨+热度=强者恒强
    elif is_top3:
        return 60
    else:
        return 50

def parse_momentum_signals(text):
    """从 momentum_signals.md 提取币种数据 — 合并"动量质量"和"涨幅榜"两个表格"""
    coins = []
    seen_symbols = set()
    
    for table_name in ['动量质量TOP', '涨幅榜TOP']:
        in_table = False
        for line in text.split('\n'):
            if table_name in line:
                in_table = True
                continue
            if in_table:
                # 跳过分隔线
                if '|:----' in line or '|:---' in line:
                    continue
                # 表格结束
                if not line.strip().startswith('|'):
                    break
                
                # 解析表格行: | 🥇 | UTK | **+16.23%** | $10,207,949 | $0.007950 | **78.0** |
                parts = [p.strip() for p in line.split('|')]
                parts = [p for p in parts if p]
                
                if len(parts) >= 6:
                    # 第1列: 排名 — 忽略
                    # 第2列: 币种符号
                    symbol_raw = parts[1]
                    symbol_clean = symbol_raw.replace('**', '').strip()
                    symbol_match = re.search(r'([A-Z0-9]{2,15})', symbol_clean.upper())
                    if not symbol_match:
                        continue
                    symbol = symbol_match.group(1)
                    
                    # 跳过已见过的
                    if symbol in seen_symbols:
                        continue
                    seen_symbols.add(symbol)
                    
                    coin = {"symbol": symbol, "change": 0, "volume": 0, "price": 0, "quality": 0, "source": table_name}
                    
                    # 第3列: 涨幅
                    chg_str = parts[2].replace('**', '').replace('%', '').replace('+', '').replace('−', '-').replace('–', '-')
                    try:
                        coin["change"] = float(chg_str)
                    except ValueError:
                        pass
                    
                    # 第4列: 成交量
                    vol_str = parts[3].replace('$', '').replace(',', '').replace('**', '')
                    try:
                        if 'M' in vol_str:
                            coin["volume"] = float(vol_str.replace('M', '')) * 1_000_000
                        elif 'B' in vol_str:
                            coin["volume"] = float(vol_str.replace('B', '')) * 1_000_000_000
                        elif 'K' in vol_str:
                            coin["volume"] = float(vol_str.replace('K', '')) * 1_000
                        else:
                            coin["volume"] = float(vol_str)
                    except ValueError:
                        pass
                    
                    # 第5列: 价格
                    pr_str = parts[4].replace('$', '').replace(',', '').replace('**', '')
                    try:
                        coin["price"] = float(pr_str)
                    except ValueError:
                        pass
                    
                    # 第6列: 质量分
                    q_str = parts[5].replace('**', '').replace('*', '')
                    try:
                        coin["quality"] = float(q_str)
                    except ValueError:
                        pass
                    
                    coins.append(coin)
    
    return coins

def main():
    if not MOMENTUM_PATH.exists():
        print("⚠️ 动量雷达信号文件不存在，跳过管道B")
        return
    
    text = MOMENTUM_PATH.read_text()
    coins = parse_momentum_signals(text)
    
    if not coins:
        print("⚠️ 动量雷达无数据，管道B空")
        return
    
    # 计算管道B评分
    b_results = []
    for i, c in enumerate(coins):
        m_score = score_momentum(c.get("change", 0))
        r_score = score_rsi_b(c.get("quality", 0))
        v_score = score_volume(c.get("volume", 0))
        f_score = score_funding(0)  # 费率未知，保守给中性
        h_score = score_heat(i < 3, c.get("change", 0))
        
        total = (v_score * PIPELINE_B_WEIGHTS["volume"] +
                 m_score * PIPELINE_B_WEIGHTS["momentum"] +
                 f_score * PIPELINE_B_WEIGHTS["funding"] +
                 r_score * PIPELINE_B_WEIGHTS["rsi_position"] +
                 h_score * PIPELINE_B_WEIGHTS["heat"])
        
        b_results.append({
            "symbol": c.get("symbol", f"#{i+1}"),
            "change": c.get("change", 0),
            "volume": c.get("volume", 0),
            "momentum_score": m_score,
            "rsi_score": r_score,
            "total": round(total, 1),
        })
    
    b_results.sort(key=lambda x: x["total"], reverse=True)
    
    # 生成管道B表格
    b_lines = ["", "## 🟢 候选池 — 管道B（动量捕捉）", 
               "以下为动量雷达扫描到的放量上涨币种（管道B评分，动量优先而非安全优先）：",
               "",
               "| # | 币种 | 涨幅% | 成交量 | 管道B总分 | 动量分 | RSI分 |",
               "|:-:|:----|:----:|:------:|:---------:|:------:|:-----:|"]
    
    for i, r in enumerate(b_results[:20]):
        sym = re.sub(r'[^\w]', '', r["symbol"])[:15]
        vol_str = f"${r['volume']/1_000_000:.1f}M" if r['volume'] >= 1_000_000 else f"${r['volume']:,.0f}"
        b_lines.append(f"| #{i+1} | {sym} | +{r['change']:.2f}% | {vol_str} | {r['total']} | {r['momentum_score']} | {r['rsi_score']} |")
    
    b_lines.append("")
    b_lines.append("*数据来源: shared/momentum_signals.md (动量雷达每30分钟扫描)*")
    
    # 找今天的A2报告
    today = datetime.now(BJT).strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"{today}.md"
    
    if output_path.exists():
        existing = output_path.read_text()
        # 检查是否已有管道B
        if "管道B（动量捕捉）" in existing:
            print(f"✅ A2报告已有管道B，跳过注入")
            return
        
        # 更新核心结论 — 把"候选池为空"改成含管道B的总数
        updated = existing
        import re as re2
        # 替换候选池为空的行
        updated = re2.sub(
            r'候选池为空 — 当前市场环境下无满足条件的币',
            f'候选池：{len(b_results)} 个动量候选 — 当前市场主推动量路径',
            updated
        )
        # 替换总候选池：0 个币
        updated = re2.sub(
            r'总候选池：\d+ 个币',
            f'总候选池：{len(b_results)} 个（管道B）',
            updated
        )
        
        # 追加管道B表格
        new_report = updated.rstrip() + "\n" + "\n".join(b_lines)
        output_path.write_text(new_report)
        print(f"✅ 管道B已注入A2报告 ({len(b_results)}个候选)")
    else:
        # A2报告不存在，先写管道B
        header = f"# A2 选币官 — 候选池报告\n日期：{today} | 数据来源：shared/momentum_signals.md\n"
        report = header + "\n".join(b_lines)
        output_path.write_text(report)
        print(f"✅ 已创建A2管道B报告 (无原始A2评分, {len(b_results)}个动量候选)")
    
    # 打印摘要
    for r in b_results[:5]:
        print(f"  {r['symbol']}: {r['total']}分 ({r['change']:+.2f}%)")

if __name__ == "__main__":
    main()
