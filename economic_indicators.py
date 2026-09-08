#!/usr/bin/env python3
"""
经济指标采集器 (Economic Indicators Collector)
功能：通过akshare采集中国+美国关键经济指标（PMI/CPI/失业率/PMI等）
替代regime_locator_v3.py中从经济日历推算PMI/CPI的近似方案

数据源：
- akshare: 中国PMI/CPI/PPI/失业率/社融
- yfinance: 美国10年期国债收益率（已有）

输出：/home/ubuntu/shared_context/macro/economic_indicators.json

Cron: 每日09:00执行（数据每日更新一次）
"""
import json, os, time, sys, traceback

SC = "/home/ubuntu/shared_context"
OUTPUT_FILE = os.path.join(SC, "macro/economic_indicators.json")
EVENTS_FILE = os.path.join(SC, "events/events.ndjson")

COUNTRIES = ["CN", "US"]


def log_event(event_type, message):
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": event_type,
        "source": "economic_indicators",
        "message": message,
    }
    os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
    with open(EVENTS_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def fetch_china_pmi():
    """中国制造业PMI（akshare）"""
    try:
        import akshare as ak
        df = ak.macro_china_pmi()
        if df is not None and len(df) > 0:
            latest = df.iloc[-1]
            month = str(latest.get("月份", ""))
            pmi_val = float(latest.get("制造业PMI", 50))
            non_mfg = float(latest.get("非制造业PMI", 50)) if "非制造业PMI" in latest else None
            return {
                "country": "CN",
                "indicator": "PMI",
                "month": month,
                "value": pmi_val,
                "non_mfg_pmi": non_mfg,
                "signal": "expanding" if pmi_val > 50 else "contracting",
                "source": "akshare",
            }
    except Exception as e:
        print(f"  [WARN] 中国PMI采集失败: {e}")
    return None


def fetch_china_cpi():
    """中国CPI同比（akshare）"""
    try:
        import akshare as ak
        df = ak.macro_china_cpi()
        if df is not None and len(df) > 0:
            latest = df.iloc[-1]
            month = str(latest.get("月份", ""))
            cpi_yoy = float(latest.get("同比", 0)) if "同比" in latest else 0
            cpi_mom = float(latest.get("环比", 0)) if "环比" in latest else 0
            return {
                "country": "CN",
                "indicator": "CPI",
                "month": month,
                "yoy": cpi_yoy,
                "mom": cpi_mom,
                "signal": "high_inflation" if cpi_yoy > 3 else ("moderate" if cpi_yoy > 1 else "low"),
                "source": "akshare",
            }
    except Exception as e:
        print(f"  [WARN] 中国CPI采集失败: {e}")
    return None


def fetch_china_ppi():
    """中国PPI同比（akshare）"""
    try:
        import akshare as ak
        df = ak.macro_china_ppi()
        if df is not None and len(df) > 0:
            latest = df.iloc[-1]
            month = str(latest.get("月份", ""))
            ppi_yoy = float(latest.get("当月同比", 0)) if "当月同比" in latest else 0
            return {
                "country": "CN",
                "indicator": "PPI",
                "month": month,
                "yoy": ppi_yoy,
                "signal": "factory_inflation" if ppi_yoy > 0 else "factory_deflation",
                "source": "akshare",
            }
    except Exception as e:
        print(f"  [WARN] 中国PPI采集失败: {e}")
    return None


def fetch_china_unemployment():
    """中国城镇失业率（akshare）"""
    try:
        import akshare as ak
        df = ak.macro_china_urban_unemployment()
        if df is not None and len(df) > 0:
            latest = df.iloc[-1]
            month = str(latest.iloc[0]) if len(latest) > 0 else ""
            rate = float(latest.iloc[1]) if len(latest) > 1 else 5.0
            return {
                "country": "CN",
                "indicator": "Unemployment",
                "month": month,
                "rate": rate,
                "signal": "high" if rate > 5.5 else ("normal" if rate > 4.5 else "low"),
                "source": "akshare",
            }
    except Exception as e:
        print(f"  [WARN] 中国失业率采集失败: {e}")
    return None


def fetch_china_social_finance():
    """中国社会融资规模存量（akshare）"""
    try:
        import akshare as ak
        df = ak.macro_china_shrzgm()
        if df is not None and len(df) > 0:
            latest = df.iloc[-1]
            month = str(latest.iloc[0]) if len(latest) > 0 else ""
            value = float(latest.iloc[1]) if len(latest) > 1 else 0
            return {
                "country": "CN",
                "indicator": "SocialFinancing",
                "month": month,
                "value_billion": value,
                "signal": "expanding" if value > 2000 else "contracting",
                "source": "akshare",
            }
    except Exception as e:
        print(f"  [WARN] 中国社融采集失败: {e}")
    return None


def fetch_us_indicators():
    """美国经济指标（从已有数据源推算）"""
    results = []

    # 美国CPI：从债券收益率推算（FED利率-10年期国债≈通胀预期）
    try:
        cb_path = os.path.join(SC, "macro/central_bank_rates.json")
        if os.path.exists(cb_path):
            with open(cb_path) as f:
                cb = json.load(f)
            fed = cb.get("central_banks", {}).get("FED", {})
            fed_rate = fed.get("current_rate", 5.0)
            bond_yield = fed.get("bond_yield", 4.0)
            inflation_expectation = fed_rate - bond_yield

            results.append({
                "country": "US",
                "indicator": "CPI_Implied",
                "fed_rate": fed_rate,
                "bond_yield": bond_yield,
                "inflation_expectation": round(inflation_expectation, 2),
                "signal": "high_inflation" if inflation_expectation > 1.5 else ("moderate" if inflation_expectation > 0.5 else "low"),
                "source": "central_bank_rates",
            })
    except Exception as e:
        print(f"  [WARN] 美国CPI推算失败: {e}")

    # 美国失业率：从经济日历提取
    try:
        cal_path = os.path.join(SC, "macro/economic_calendar.json")
        if os.path.exists(cal_path):
            with open(cal_path) as f:
                cal = json.load(f)
            unemployment_events = [
                e for e in cal.get("events", [])
                if "unemployment" in e.get("title", "").lower() or "非农" in e.get("title", "")
            ]
            if unemployment_events:
                latest = unemployment_events[0]
                results.append({
                    "country": "US",
                    "indicator": "Unemployment_Event",
                    "title": latest.get("title", ""),
                    "date": latest.get("date", ""),
                    "impact": latest.get("impact", "C"),
                    "actual": latest.get("actual", ""),
                    "forecast": latest.get("forecast", ""),
                    "source": "economic_calendar",
                })
    except Exception as e:
        print(f"  [WARN] 美国失业率事件提取失败: {e}")

    return results


def collect_all():
    """采集所有经济指标"""
    print("[经济指标] 开始采集...")
    all_indicators = []
    fetch_count = 0
    fail_count = 0

    # 中国指标
    cn_fetchers = [
        ("PMI", fetch_china_pmi),
        ("CPI", fetch_china_cpi),
        ("PPI", fetch_china_ppi),
        ("Unemployment", fetch_china_unemployment),
        ("SocialFinancing", fetch_china_social_finance),
    ]

    for name, fetcher in cn_fetchers:
        print(f"  采集中国{name}...")
        result = fetcher()
        if result:
            all_indicators.append(result)
            fetch_count += 1
            print(f"    ✓ {name}: {result.get('month', '')} = {result.get('value', result.get('yoy', result.get('rate', '?')))}")
        else:
            fail_count += 1
            print(f"    ✗ {name}: 采集失败")

    # 美国指标
    print("  采集美国指标...")
    us_results = fetch_us_indicators()
    for r in us_results:
        all_indicators.append(r)
        fetch_count += 1
        print(f"    ✓ {r['indicator']}: {r.get('signal', '?')}")

    # 汇总
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "date": time.strftime("%Y-%m-%d"),
        "total_indicators": len(all_indicators),
        "success": fetch_count,
        "failed": fail_count,
        "indicators": all_indicators,
        # 便捷字段供regime_locator_v3读取
        "cn_pmi": next((i for i in all_indicators if i.get("indicator") == "PMI"), None),
        "cn_cpi": next((i for i in all_indicators if i.get("indicator") == "CPI"), None),
        "cn_ppi": next((i for i in all_indicators if i.get("indicator") == "PPI"), None),
        "cn_unemployment": next((i for i in all_indicators if i.get("indicator") == "Unemployment"), None),
        "cn_social_financing": next((i for i in all_indicators if i.get("indicator") == "SocialFinancing"), None),
        "us_cpi_implied": next((i for i in all_indicators if i.get("indicator") == "CPI_Implied"), None),
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    log_event("macro.indicators", f"经济指标采集: {fetch_count}成功/{fail_count}失败")
    print(f"\n[经济指标] 完成: {fetch_count}成功/{fail_count}失败")
    print(f"  输出: {OUTPUT_FILE}")
    return report


if __name__ == "__main__":
    report = collect_all()
    print(f"\n--- 摘要 ---")
    for ind in report["indicators"]:
        val = ind.get("value", ind.get("yoy", ind.get("rate", ind.get("inflation_expectation", "?"))))
        print(f"  {ind['country']} {ind['indicator']}: {val} ({ind.get('signal', '')})")
