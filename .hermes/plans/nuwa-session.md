# Nuwa Multi-View Market Analysis Plan

## Objective
Load 4 persona skills, analyze today's market from 4 perspectives, produce a multi-view judgment matrix for ZH and A3 reference.

## Data Sources
- profiles/a1-data/output/ - A1 data collection output (F&G, funding rate, BTC price, etc.)
- profiles/a2-selector/output/ - A2 candidate pool report
- state/a3.json - A3 signals
- state/persona_today.txt - today's rotation persona
- shared/direction_priority_*.md - ZH direction fusion output

## Personas to Load
1. arthur-hayes-perspective → Macro liquidity
2. benjamin-cowen → Cycle positioning
3. willy-woo → On-chain data
4. ansem → Narrative/sentiment/meme

## Output
Write to profiles/zh/output/nuwa_multi_view_YYYY-MM-DD.md
