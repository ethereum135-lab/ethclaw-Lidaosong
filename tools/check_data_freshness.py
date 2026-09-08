#!/usr/bin/env python3
"""数据新鲜度自检 — 检查所有关键数据文件是否在预期时效内

用法: python3 tools/check_data_freshness.py [--warn-only]
输出: 报告哪些文件过期，exit_code=0全新鲜，1有过期

防御等级: 🔴硬防御（数据是关键路径，过期导致系统盲飞）
"""

import os, json, time, sys
from datetime import datetime

ZQ_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHECKS = [
    # (path, max_hours, name, critical)
    ('data/gainer_coverage.json', 24, '涨幅榜覆盖复盘', True),
    ('data/signals.json', 2, 'A3信号扫描', True),
    ('data/coin_pool.json', 48, '选币库全量池', False),
    ('data/coin_pool_prime.json', 48, '精选池', False),
    ('data/score_db.json', 24, '评分库', False),
    ('data/signals/a4_signals.json', 6, 'A4信号', True),
    ('data/experience/MASTER_EXPERIENCE.json', 24, '主经验档案', False),
]

def main():
    now = time.time()
    stale = []
    ok = []
    missing = []

    for rel_path, max_hours, name, critical in CHECKS:
        full = os.path.join(ZQ_DIR, rel_path)
        if not os.path.exists(full):
            missing.append((name, rel_path, critical))
            continue

        mtime = os.path.getmtime(full)
        hours_ago = (now - mtime) / 3600
        
        # 特殊检查：a4_signals.json generated_at是否存在
        extra_note = ''
        if 'a4_signals' in rel_path:
            try:
                with open(full) as f:
                    data = json.load(f)
                if not data.get('generated_at'):
                    extra_note = ' ⚠️ 无generated_at字段'
                elif isinstance(data, dict) and data.get('buy_signals') is not None:
                    n_buy = len(data.get('buy_signals', []))
                    n_sell = len(data.get('sell_signals', []))
                    if n_buy == 0 and n_sell == 0:
                        extra_note = f' (空信号: buy=0 sell=0)'
            except:
                pass

        mt_str = datetime.fromtimestamp(mtime).strftime('%m-%d %H:%M')
        pct = hours_ago / max_hours * 100
        
        if hours_ago > max_hours:
            stale.append((name, rel_path, mt_str, hours_ago, max_hours, critical, extra_note))
        else:
            ok.append((name, rel_path, mt_str, hours_ago, max_hours, pct))

    # 输出报告
    print("=" * 55)
    print(f"📊 数据新鲜度自检 | {datetime.now().strftime('%m-%d %H:%M')}")
    print("=" * 55)

    if stale:
        print(f"\n❌ 过期文件 ({len(stale)}个):")
        for name, path, mt, age, limit, critical, note in stale:
            flag = '🔴关键' if critical else '⚠️'
            print(f"  {flag} {name} ({os.path.basename(path)})")
            print(f"     最后更新: {mt} | {age:.0f}h前 (阈值: {limit}h){note}")
    else:
        print("\n✅ 所有文件都在时效内")

    if missing:
        print(f"\n❌ 缺失文件 ({len(missing)}个):")
        for name, path, critical in missing:
            flag = '🔴关键' if critical else '⚠️'
            print(f"  {flag} {name} ({path})")

    if ok:
        print(f"\n✅ 新鲜文件 ({len(ok)}个):")
        for name, path, mt, age, limit, pct in ok[:5]:
            bar = '█' * int(pct/10) + '░' * (10 - int(pct/10))
            print(f"  {name}: {mt} ({age:.0f}h前) [{bar}]")

    any_critical_stale = any(c for _,_,_,_,_,c,_ in stale)
    any_missing_critical = any(c for _,_,c in missing if c)
    
    print(f"\n{'🔴 关键文件过期!' if any_critical_stale or any_missing_critical else '✅ 关键文件都新鲜'}")
    
    return 1 if (any_critical_stale or any_missing_critical) else 0

if __name__ == '__main__':
    sys.exit(main())
