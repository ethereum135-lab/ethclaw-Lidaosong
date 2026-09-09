#!/usr/bin/env python3
"""
WorkBuddy 视觉内容生成器 — 生成 SVG 海报/信息图/数据卡片
纯 Python + SVG，无需外部依赖，服务器上直接可用

用法:
    python3 content_visual_generator.py --type daily_card  # 每日行情海报
    python3 content_visual_generator.py --type market_regime  # 市场制度图
    python3 content_visual_generator.py --type debate_summary  # 辩论结果卡
    python3 content_visual_generator.py --type risk_status  # 风控状态卡
"""
import json
import os
import sys
import time
from datetime import datetime

SC = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(SC, "content", "visual")
os.makedirs(CONTENT_DIR, exist_ok=True)

# 配色方案
COLORS = {
    "bg_dark": "#0f172a",
    "bg_card": "#1e293b",
    "bg_highlight": "#334155",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "accent_green": "#22c55e",
    "accent_red": "#ef4444",
    "accent_yellow": "#eab308",
    "accent_blue": "#3b82f6",
    "accent_purple": "#a855f7",
    "accent_cyan": "#06b6d4",
    "border": "#334155",
}


def _read_json(path, default=None):
    """读取JSON文件"""
    try:
        with open(os.path.join(SC, path)) as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def _save_svg(svg_content, filename):
    """保存SVG文件"""
    path = os.path.join(CONTENT_DIR, filename)
    with open(path, "w") as f:
        f.write(svg_content)
    return path


def generate_daily_card():
    """生成每日行情数据卡片 (800x1000)"""
    fg = _read_json("macro/fear_greed.json", {"value": 50, "classification": "Neutral"})
    debate = _read_json("strategy/debate_result.json", {})
    risk = _read_json("risk/risk_status.json", {})
    positions = _read_json("trades/positions.json", {"positions": []})
    market_regime = _read_json("macro/market_regime.json", {})
    dashboard = _read_json("macro/dashboard.json", {})

    fg_val = fg.get("value", 50)
    fg_class = fg.get("classification", "Neutral")
    decision = debate.get("decision", "HOLD")
    confidence = debate.get("confidence", 0)
    risk_status = risk.get("status", "OK")
    pos_count = len(positions.get("positions", []))
    regime = market_regime.get("regime", "unknown")
    usdt_balance = debate.get("usdt_balance", 0)
    pnl = debate.get("daily_pnl", 0)

    # 恐惧贪婪颜色
    if fg_val < 25:
        fg_color = COLORS["accent_red"]
    elif fg_val < 45:
        fg_color = COLORS["accent_yellow"]
    elif fg_val < 55:
        fg_color = COLORS["text_secondary"]
    elif fg_val < 75:
        fg_color = COLORS["accent_green"]
    else:
        fg_color = COLORS["accent_yellow"]

    # 决策颜色
    if decision == "BUY":
        dec_color = COLORS["accent_green"]
    elif decision == "SELL":
        dec_color = COLORS["accent_red"]
    else:
        dec_color = COLORS["accent_yellow"]

    # 风险颜色
    risk_color = COLORS["accent_green"] if risk_status == "OK" else COLORS["accent_red"]

    date_str = time.strftime("%Y-%m-%d")
    day_str = time.strftime("%A")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1000" width="800" height="1000">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['bg_dark']}"/>
      <stop offset="100%" style="stop-color:#1a1a2e"/>
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['bg_card']}"/>
      <stop offset="100%" style="stop-color:{COLORS['bg_highlight']}"/>
    </linearGradient>
  </defs>

  <!-- 背景 -->
  <rect width="800" height="1000" fill="url(#bgGrad)"/>

  <!-- 标题区 -->
  <text x="40" y="60" fill="{COLORS['text_primary']}" font-size="32" font-weight="bold" font-family="Arial, sans-serif">
    📊 每日行情速报
  </text>
  <text x="40" y="90" fill="{COLORS['text_secondary']}" font-size="18" font-family="Arial, sans-serif">
    {date_str} {day_str}
  </text>
  <line x1="40" y1="110" x2="760" y2="110" stroke="{COLORS['border']}" stroke-width="2"/>

  <!-- 恐惧贪婪指数 -->
  <rect x="40" y="140" width="340" height="180" rx="12" fill="url(#cardGrad)"/>
  <text x="60" y="175" fill="{COLORS['text_secondary']}" font-size="16" font-family="Arial, sans-serif">
    恐惧贪婪指数
  </text>
  <text x="60" y="235" fill="{fg_color}" font-size="56" font-weight="bold" font-family="Arial, sans-serif">
    {fg_val}
  </text>
  <text x="180" y="235" fill="{fg_color}" font-size="24" font-weight="bold" font-family="Arial, sans-serif">
    {fg_class}
  </text>
  <!-- 进度条 -->
  <rect x="60" y="260" width="300" height="8" rx="4" fill="{COLORS['bg_highlight']}"/>
  <rect x="60" y="260" width="{fg_val * 3}" height="8" rx="4" fill="{fg_color}"/>
  <text x="60" y="295" fill="{COLORS['text_secondary']}" font-size="12" font-family="Arial, sans-serif">
    极度恐惧 ←————————————→ 极度贪婪
  </text>

  <!-- 多空决策 -->
  <rect x="420" y="140" width="340" height="180" rx="12" fill="url(#cardGrad)"/>
  <text x="440" y="175" fill="{COLORS['text_secondary']}" font-size="16" font-family="Arial, sans-serif">
    AI 多空决策
  </text>
  <text x="440" y="235" fill="{dec_color}" font-size="56" font-weight="bold" font-family="Arial, sans-serif">
    {decision}
  </text>
  <text x="640" y="235" fill="{COLORS['text_secondary']}" font-size="20" font-family="Arial, sans-serif">
    信心 {confidence}%
  </text>
  <text x="440" y="275" fill="{COLORS['text_secondary']}" font-size="14" font-family="Arial, sans-serif">
    {debate.get('reason', '')[:50]}
  </text>

  <!-- 市场制度 -->
  <rect x="40" y="350" width="220" height="140" rx="12" fill="url(#cardGrad)"/>
  <text x="60" y="385" fill="{COLORS['text_secondary']}" font-size="14" font-family="Arial, sans-serif">
    市场制度
  </text>
  <text x="60" y="430" fill="{COLORS['accent_cyan']}" font-size="28" font-weight="bold" font-family="Arial, sans-serif">
    {regime}
  </text>

  <!-- 持仓 -->
  <rect x="280" y="350" width="220" height="140" rx="12" fill="url(#cardGrad)"/>
  <text x="300" y="385" fill="{COLORS['text_secondary']}" font-size="14" font-family="Arial, sans-serif">
    当前持仓
  </text>
  <text x="300" y="430" fill="{COLORS['accent_blue']}" font-size="36" font-weight="bold" font-family="Arial, sans-serif">
    {pos_count} 个
  </text>

  <!-- 风控状态 -->
  <rect x="520" y="350" width="240" height="140" rx="12" fill="url(#cardGrad)"/>
  <text x="540" y="385" fill="{COLORS['text_secondary']}" font-size="14" font-family="Arial, sans-serif">
    风控状态
  </text>
  <text x="540" y="430" fill="{risk_color}" font-size="32" font-weight="bold" font-family="Arial, sans-serif">
    ● {risk_status}
  </text>

  <!-- 资产 -->
  <rect x="40" y="520" width="720" height="120" rx="12" fill="url(#cardGrad)"/>
  <text x="60" y="555" fill="{COLORS['text_secondary']}" font-size="14" font-family="Arial, sans-serif">
    账户资产
  </text>
  <text x="60" y="605" fill="{COLORS['text_primary']}" font-size="36" font-weight="bold" font-family="Arial, sans-serif">
    ${usdt_balance:.2f} USDT
  </text>
  <text x="350" y="605" fill="{COLORS['accent_green'] if pnl >= 0 else COLORS['accent_red']}" font-size="28" font-weight="bold" font-family="Arial, sans-serif">
    {'+' if pnl >= 0 else ''}{pnl:.2f} 今日
  </text>

  <!-- 策略维度分数 -->
  <rect x="40" y="670" width="720" height="250" rx="12" fill="url(#cardGrad)"/>
  <text x="60" y="705" fill="{COLORS['text_secondary']}" font-size="16" font-family="Arial, sans-serif">
    多维度评分
  </text>
'''

    scores = debate.get("scores", {})
    score_labels = {
        "momentum": "动量",
        "trend_filter": "趋势过滤",
        "fg_reversal": "F&G反转",
        "volatility": "波动率",
        "position_mgmt": "仓位管理",
        "sentiment": "情绪",
        "cross_market": "跨市场",
    }

    y = 740
    for key, label in score_labels.items():
        score = scores.get(key, 0)
        # 分数归一化到 0-100
        bar_width = max(0, min(100, (score + 100) / 2))
        bar_color = COLORS["accent_green"] if score > 0 else COLORS["accent_red"] if score < 0 else COLORS["text_secondary"]

        svg += f'''  <text x="60" y="{y}" fill="{COLORS['text_secondary']}" font-size="14" font-family="Arial, sans-serif">{label}</text>
  <rect x="160" y="{y - 12}" width="400" height="14" rx="3" fill="{COLORS['bg_highlight']}"/>
  <rect x="160" y="{y - 12}" width="{bar_width * 4}" height="14" rx="3" fill="{bar_color}"/>
  <text x="580" y="{y}" fill="{COLORS['text_primary']}" font-size="14" font-family="Arial, sans-serif">{score:+.1f}</text>
'''
        y += 28

    svg += f'''
  <!-- 底部 -->
  <text x="40" y="970" fill="{COLORS['text_secondary']}" font-size="12" font-family="Arial, sans-serif">
    由 ZQ Web4.0 多智能体系统自动生成 · WorkBuddy
  </text>
</svg>'''

    filename = f"daily_card_{date_str}.svg"
    path = _save_svg(svg, filename)
    print(f"✅ 每日行情海报已生成: {path}")
    return path


def generate_debate_summary_card():
    """生成辩论结果摘要卡片"""
    debate = _read_json("strategy/debate_result.json", {})
    rule_library = _read_json("macro/rule_library.json", {"matched_rules": []})
    risk = _read_json("risk/risk_status.json", {})

    decision = debate.get("decision", "HOLD")
    confidence = debate.get("confidence", 0)
    intensity = debate.get("intensity", "neutral")
    reason = debate.get("reason", "")
    action = debate.get("action", "")
    matched_rules = rule_library.get("matched_rules", [])
    risk_level = risk.get("level", "NORMAL")

    dec_color = COLORS["accent_green"] if decision == "BUY" else COLORS["accent_red"] if decision == "SELL" else COLORS["accent_yellow"]
    date_str = time.strftime("%Y-%m-%d %H:%M")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 800" width="600" height="800">
  <defs>
    <linearGradient id="bgGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['bg_dark']}"/>
      <stop offset="100%" style="stop-color:#1a1a2e"/>
    </linearGradient>
  </defs>
  <rect width="600" height="800" fill="url(#bgGrad2)"/>

  <text x="30" y="50" fill="{COLORS['text_primary']}" font-size="24" font-weight="bold" font-family="Arial, sans-serif">
    🧠 AI 多空辩论结果
  </text>
  <text x="30" y="75" fill="{COLORS['text_secondary']}" font-size="14" font-family="Arial, sans-serif">
    {date_str}
  </text>
  <line x1="30" y1="90" x2="570" y2="90" stroke="{COLORS['border']}" stroke-width="1"/>

  <!-- 决策 -->
  <text x="30" y="160" fill="{dec_color}" font-size="80" font-weight="bold" font-family="Arial, sans-serif">
    {decision}
  </text>
  <text x="30" y="200" fill="{COLORS['text_secondary']}" font-size="20" font-family="Arial, sans-serif">
    信心: {confidence}% · 强度: {intensity}
  </text>

  <!-- 信心条 -->
  <rect x="30" y="220" width="540" height="12" rx="6" fill="{COLORS['bg_highlight']}"/>
  <rect x="30" y="220" width="{confidence * 5.4}" height="12" rx="6" fill="{dec_color}"/>

  <!-- 理由 -->
  <rect x="30" y="260" width="540" height="80" rx="8" fill="{COLORS['bg_card']}"/>
  <text x="50" y="290" fill="{COLORS['text_secondary']}" font-size="13" font-family="Arial, sans-serif">
    决策理由
  </text>
  <text x="50" y="315" fill="{COLORS['text_primary']}" font-size="14" font-family="Arial, sans-serif">
    {reason[:60]}
  </text>

  <!-- 操作建议 -->
  <rect x="30" y="360" width="540" height="60" rx="8" fill="{COLORS['bg_card']}"/>
  <text x="50" y="395" fill="{COLORS['accent_cyan']}" font-size="16" font-weight="bold" font-family="Arial, sans-serif">
    💡 {action}
  </text>

  <!-- 匹配规则 -->
  <text x="30" y="450" fill="{COLORS['text_secondary']}" font-size="16" font-family="Arial, sans-serif">
    📋 触发规则 ({len(matched_rules)}条)
  </text>
'''

    y = 480
    for i, rule in enumerate(matched_rules[:6]):
        if isinstance(rule, str):
            rule_id = rule
            rule_desc = ""
            priority = 0
            learning_note = ""
        else:
            rule_id = rule.get("rule_id", rule.get("id", "?"))
            rule_desc = rule.get("description", rule.get("name", ""))[:40]
            priority = rule.get("priority", 0)
            learning_note = rule.get("_learning_adjusted", "")

        svg += f'''  <rect x="30" y="{y - 20}" width="540" height="32" rx="6" fill="{COLORS['bg_card']}"/>
  <text x="50" y="{y}" fill="{COLORS['text_primary']}" font-size="13" font-family="Arial, sans-serif">
    {rule_id} {rule_desc}
  </text>
  <text x="500" y="{y}" fill="{COLORS['text_secondary']}" font-size="11" font-family="Arial, sans-serif">
    P{priority}
  </text>
'''
        if learning_note:
            svg += f'''  <text x="50" y="{y + 14}" fill="{COLORS['accent_yellow']}" font-size="10" font-family="Arial, sans-serif">
    🧠 {learning_note}
  </text>
'''
            y += 14
        y += 40

    svg += f'''
  <!-- 风控级别 -->
  <rect x="30" y="720" width="540" height="50" rx="8" fill="{COLORS['bg_card']}"/>
  <text x="50" y="752" fill="{COLORS['text_secondary']}" font-size="14" font-family="Arial, sans-serif">
    风控级别: <tspan fill="{COLORS['accent_yellow']}" font-weight="bold">{risk_level}</tspan>
  </text>

  <text x="30" y="785" fill="{COLORS['text_secondary']}" font-size="11" font-family="Arial, sans-serif">
    TraeCode 辩论引擎 v4.0 · 学习闭环已启用
  </text>
</svg>'''

    filename = f"debate_summary_{time.strftime('%Y%m%d_%H%M')}.svg"
    path = _save_svg(svg, filename)
    print(f"✅ 辩论摘要卡已生成: {path}")
    return path


def generate_risk_status_card():
    """生成风控状态卡片"""
    risk = _read_json("risk/risk_status.json", {})
    positions = _read_json("trades/positions.json", {"positions": []})
    stop_audit = _read_json("risk/stop_order_audit.json", {"normal": 0, "naked": 0})

    status = risk.get("status", "OK")
    level = risk.get("level", "NORMAL")
    consec_losses = risk.get("consecutive_losses", 0)
    daily_loss_pct = risk.get("daily_loss_pct", 0)
    total_exposure = risk.get("total_exposure", 0)

    status_color = COLORS["accent_green"] if status == "OK" else COLORS["accent_red"]
    date_str = time.strftime("%Y-%m-%d %H:%M")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 500" width="600" height="500">
  <defs>
    <linearGradient id="bgGrad3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['bg_dark']}"/>
      <stop offset="100%" style="stop-color:#1a1a2e"/>
    </linearGradient>
  </defs>
  <rect width="600" height="500" fill="url(#bgGrad3)"/>

  <text x="30" y="50" fill="{COLORS['text_primary']}" font-size="24" font-weight="bold" font-family="Arial, sans-serif">
    🛡️ 风控状态
  </text>
  <text x="30" y="75" fill="{COLORS['text_secondary']}" font-size="14" font-family="Arial, sans-serif">
    {date_str}
  </text>

  <!-- 状态 -->
  <circle cx="300" cy="180" r="70" fill="none" stroke="{status_color}" stroke-width="6"/>
  <text x="300" y="190" fill="{status_color}" font-size="36" font-weight="bold" text-anchor="middle" font-family="Arial, sans-serif">
    {status}
  </text>
  <text x="300" y="220" fill="{COLORS['text_secondary']}" font-size="14" text-anchor="middle" font-family="Arial, sans-serif">
    级别: {level}
  </text>

  <!-- 指标 -->
  <rect x="30" y="290" width="260" height="80" rx="8" fill="{COLORS['bg_card']}"/>
  <text x="50" y="320" fill="{COLORS['text_secondary']}" font-size="13" font-family="Arial, sans-serif">连亏次数</text>
  <text x="50" y="355" fill="{COLORS['accent_red'] if consec_losses > 0 else COLORS['accent_green']}" font-size="28" font-weight="bold" font-family="Arial, sans-serif">{consec_losses}</text>

  <rect x="310" y="290" width="260" height="80" rx="8" fill="{COLORS['bg_card']}"/>
  <text x="330" y="320" fill="{COLORS['text_secondary']}" font-size="13" font-family="Arial, sans-serif">持仓数</text>
  <text x="330" y="355" fill="{COLORS['accent_blue']}" font-size="28" font-weight="bold" font-family="Arial, sans-serif">{len(positions.get('positions', []))}</text>

  <rect x="30" y="390" width="540" height="60" rx="8" fill="{COLORS['bg_card']}"/>
  <text x="50" y="415" fill="{COLORS['text_secondary']}" font-size="13" font-family="Arial, sans-serif">止损单校验</text>
  <text x="200" y="415" fill="{COLORS['accent_green']}" font-size="18" font-weight="bold" font-family="Arial, sans-serif">{stop_audit.get('normal', 0)} 正常</text>
  <text x="350" y="415" fill="{COLORS['accent_red']}" font-size="18" font-weight="bold" font-family="Arial, sans-serif">{stop_audit.get('naked', 0)} 裸奔</text>

  <text x="30" y="480" fill="{COLORS['text_secondary']}" font-size="11" font-family="Arial, sans-serif">
    OpenClaw 风控监控 · 每5分钟检查
  </text>
</svg>'''

    filename = f"risk_status_{time.strftime('%Y%m%d')}.svg"
    path = _save_svg(svg, filename)
    print(f"✅ 风控状态卡已生成: {path}")
    return path


def main():
    """主入口"""
    import argparse
    parser = argparse.ArgumentParser(description="WorkBuddy 视觉内容生成器")
    parser.add_argument("--type", default="daily_card",
                        choices=["daily_card", "debate_summary", "risk_status", "all"],
                        help="生成类型")
    args = parser.parse_args()

    generated = []
    if args.type in ("daily_card", "all"):
        generated.append(generate_daily_card())
    if args.type in ("debate_summary", "all"):
        generated.append(generate_debate_summary_card())
    if args.type in ("risk_status", "all"):
        generated.append(generate_risk_status_card())

    print(f"\n🎉 已生成 {len(generated)} 张视觉卡片")
    print(f"输出目录: {CONTENT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
