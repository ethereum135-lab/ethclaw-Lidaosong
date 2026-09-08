#!/bin/bash
# 每日人物轮训推进脚本 — 每次执行将 persona_today.txt 切换到下一个人
PERSONS=(changpeng-zhao vitalik-buterin michael-saylor justin-sun willy-woo raoul-pal shen-yu xumingxing andreas-antonopoulos jihan-wu ansem sbf brian-armstrong do-kwon barry-silbert anatoly-yakovenko mike-novogratz murad-mahmudov benjamin-cowen lyn-alden james-check hasu arthur-hayes-perspective)
FILE="/Users/lidaosong/zq_web4_trading_system/state/persona_today.txt"
CURRENT=$(cat "$FILE" 2>/dev/null || echo "willy-woo")
IDX=-1
for i in "${!PERSONS[@]}"; do
  if [ "${PERSONS[$i]}" = "$CURRENT" ]; then IDX=$i; break; fi
done
NEXT_IDX=$(( (IDX + 1) % ${#PERSONS[@]} ))
echo "${PERSONS[$NEXT_IDX]}" > "$FILE"
echo "${PERSONS[$NEXT_IDX]}"
