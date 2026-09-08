#!/usr/bin/env python3
"""
期权隐含波动率采集器 (Options Implied Volatility Collector)
功能：通过yfinance采集主流ETF/指数的期权隐含波动率(IV)
纳入分析层，作为VIX的补充指标

数据源：yfinance options API
采集品种：SPY, QQQ, IWM, EEM, GLD, USO
输出：macro/options_iv.json

Cron: 每日17:00（美股开盘后）
"""
import json, os, time, sys

SC = "/home/ubuntu/shared_context"
OUTPUT_FILE = os.path.join(SC, "macro/options_iv.json")
EVENTS_FILE = os.path.join(SC, "events/events.ndjson")

SYMBOLS = [
    {"symbol": "SPY", "name": "标普500ETF", "category": "大盘"},
    {"symbol": "QQQ", "name": "纳斯达克ETF", "category": "科技"},
    {"symbol": "IWM", "name": "罗素2000ETF", "category": "小盘"},
    {"symbol": "EEM", "name": "新兴市场ETF", "category": "新兴"},
    {"symbol": "GLD", "name": "黄金ETF", "category": "大宗"},
    {"symbol": "USO", "name": "原油ETF", "category": "大宗"},
]


def _log_event(event_type, message):
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": event_type,
        "source": "options_iv",
        "message": message,
    }
    os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
    with open(EVENTS_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def fetch_iv(symbol_info):
    symbol = symbol_info["symbol"]
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        exp_dates = ticker.options
        if not exp_dates:
            return {"symbol": symbol, "name": symbol_info["name"], "status": "no_options", "iv": None}
        near_date = exp_dates[0]
        far_date = exp_dates[1] if len(exp_dates) > 1 else None
        near_chain = ticker.option_chain(near_date)
        calls = near_chain.calls
        puts = near_chain.puts
        current_price = ticker.fast_info.get("last_price", 0) or ticker.fast_info.get("lastPrice", 0)
        if current_price == 0:
            hist = ticker.history(period="1d")
            current_price = hist["Close"].iloc[-1] if len(hist) > 0 else 0
        if current_price == 0 or len(calls) == 0:
            return {"symbol": symbol, "name": symbol_info["name"], "status": "no_price", "iv": None}
        atm_call = calls.iloc[(calls["strike"] - current_price).abs().argsort()[:1]]
        atm_put = puts.iloc[(puts["strike"] - current_price).abs().argsort()[:1]]
        call_iv = float(atm_call["impliedVolatility"].iloc[0]) if len(atm_call) > 0 else None
        put_iv = float(atm_put["impliedVolatility"].iloc[0]) if len(atm_put) > 0 else None
        atm_iv = None
        if call_iv and put_iv:
            atm_iv = round((call_iv + put_iv) / 2, 4)
        elif call_iv:
            atm_iv = round(call_iv, 4)
        elif put_iv:
            atm_iv = round(put_iv, 4)
        skew = round(put_iv - call_iv, 4) if call_iv and put_iv else None
        far_iv = None
        if far_date:
            far_chain = ticker.option_chain(far_date)
            far_calls = far_chain.calls
            far_puts = far_chain.puts
            if len(far_calls) > 0 and len(far_puts) > 0:
                far_atm_call = far_calls.iloc[(far_calls["strike"] - current_price).abs().argsort()[:1]]
                far_atm_put = far_puts.iloc[(far_puts["strike"] - current_price).abs().argsort()[:1]]
                f_call_iv = float(far_atm_call["impliedVolatility"].iloc[0]) if len(far_atm_call) > 0 else None
                f_put_iv = float(far_atm_put["impliedVolatility"].iloc[0]) if len(far_atm_put) > 0 else None
                if f_call_iv and f_put_iv:
                    far_iv = round((f_call_iv + f_put_iv) / 2, 4)
        term_structure = None
        if atm_iv and far_iv:
            term_structure = "contango" if far_iv > atm_iv else "backwardation"
        return {
            "symbol": symbol, "name": symbol_info["name"], "category": symbol_info["category"],
            "current_price": round(current_price, 2), "near_expiry": near_date, "far_expiry": far_date,
            "atm_iv": atm_iv, "call_iv": round(call_iv, 4) if call_iv else None,
            "put_iv": round(put_iv, 4) if put_iv else None, "skew": skew,
            "far_iv": far_iv, "term_structure": term_structure, "status": "ok",
        }
    except Exception as e:
        return {"symbol": symbol, "name": symbol_info["name"], "status": "error", "error": str(e)}


def collect_all():
    print("[期权IV] 开始采集...")
    results = []
    ok_count = 0
    fail_count = 0
    for s in SYMBOLS:
        print(f"  采集 {s['symbol']} ({s['name']})...")
        r = fetch_iv(s)
        results.append(r)
        if r.get("status") == "ok":
            ok_count += 1
            iv_pct = r.get("atm_iv", 0) or 0
            print(f"    OK IV={iv_pct*100:.1f}% skew={r.get('skew')} term={r.get('term_structure')}")
        else:
            fail_count += 1
            print(f"    FAIL {r.get('status', 'error')}: {r.get('error', '')}")
    ivs = [r["atm_iv"] for r in results if r.get("atm_iv")]
    avg_iv = round(sum(ivs) / len(ivs), 4) if ivs else None
    skews = [r["skew"] for r in results if r.get("skew") is not None]
    avg_skew = round(sum(skews) / len(skews), 4) if skews else None
    backwardations = sum(1 for r in results if r.get("term_structure") == "backwardation")
    if avg_iv:
        if avg_iv > 0.40: iv_signal = "extreme_fear"
        elif avg_iv > 0.25: iv_signal = "elevated"
        elif avg_iv > 0.15: iv_signal = "normal"
        else: iv_signal = "complacent"
    else:
        iv_signal = "no_data"
    if avg_skew and avg_skew > 0.05: skew_signal = "bearish"
    elif avg_skew and avg_skew > 0: skew_signal = "slightly_bearish"
    else: skew_signal = "neutral"
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "date": time.strftime("%Y-%m-%d"),
        "total_symbols": len(SYMBOLS), "success": ok_count, "failed": fail_count,
        "avg_atm_iv": avg_iv, "avg_skew": avg_skew, "backwardation_count": backwardations,
        "iv_signal": iv_signal, "skew_signal": skew_signal,
        "overall_signal": f"IV={iv_signal}, Skew={skew_signal}",
        "details": results,
    }
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    _log_event("macro.options_iv", f"期权IV采集: {ok_count}/{len(SYMBOLS)}成功, IV信号={iv_signal}")
    print(f"\n[期权IV] 完成: {ok_count}/{len(SYMBOLS)}成功")
    if avg_iv: print(f"  平均IV: {avg_iv*100:.1f}%")
    print(f"  IV信号: {iv_signal}")
    print(f"  Skew信号: {skew_signal}")
    return report


if __name__ == "__main__":
    collect_all()
