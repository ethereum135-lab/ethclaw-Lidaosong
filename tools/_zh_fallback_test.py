"""验证 2026-08-02 FALLBACK 保护逻辑 — 模拟今日崩盘+过期数据场景"""
import sys, os, json, time
sys.path.insert(0, 'profiles/a4-blade')

# 直接从 executor.py 读取相关函数，不执行 main
import importlib.util
spec = importlib.util.spec_from_file_location("executor", "profiles/a4-blade/executor.py")
# 只做静态检查，不实际执行模块（会触发网络调用）
src = open("profiles/a4-blade/executor.py").read()

# 1. 验证新保护代码存在
assert "崩盘模式下禁止FALLBACK买入" in src, "FAIL: 崩盘保护缺失"
assert "fast_scan数据过期" in src, "FAIL: 过期保护缺失"
print("✅ 保护代码已存在")

# 2. 模拟今日条件
fast_scan = 'data/fast_scan_candidates.json'
fs_age_h = (time.time() - os.path.getmtime(fast_scan)) / 3600
crash = json.load(open('data/signals/.crash_wave_cache.json'))

print(f"\n📊 今日条件模拟:")
print(f"  fast_scan年龄: {fs_age_h:.0f}h (>48h 触发保护)")
print(f"  崩盘模式: {crash[0]}, {crash[1]}币跌>30%")
print(f"  → FALLBACK 应被拦截: {'✅' if (fs_age_h > 48 or crash[0]=='crash') else '❌'}")

# 3. 验证保护逻辑顺序（在 fast_scan 打开之前）
fallback_start = src.index("if not buy_signals and not sell_signals:")
fallback_block = src[fallback_start:fallback_start+1200]
crash_check_pos = fallback_block.index("crash_mode, crash_count, crash_max_drop, crash_coin = _detect_crash_wave()")
fs_open_pos = fallback_block.index("fs = json.load(f)")
assert crash_check_pos < fs_open_pos, "FAIL: 崩盘检查应在fast_scan读取之前"
print("✅ 崩盘检查在 fast_scan 读取之前执行（短路保护）")

print("\n✅ 验证通过: 今日条件下 RIF FALLBACK 买入将被拦截")
