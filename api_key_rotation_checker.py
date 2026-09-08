#!/usr/bin/env python3
"""
API密钥轮换检查器 (API Key Rotation Checker)
功能：检查所有API密钥的最后轮换日期，到期提醒+自动生成轮换指引

检查规则：
- 每90天需要轮换一次
- 75-90天：WARNING提醒
- >90天：CRITICAL告警

输出：risk/api_key_rotation.json + alerts
Cron: 每日09:30
"""
import json, os, time, sys

SC = "/home/ubuntu/shared_context"
OUTPUT_FILE = os.path.join(SC, "risk/api_key_rotation.json")
ALERT_FILE = os.path.join(SC, "alerts/api_key_rotation.json")
EVENTS_FILE = os.path.join(SC, "events/events.ndjson")
ROTATION_LOG = os.path.join(SC, "risk/key_rotation_log.json")

ROTATION_DAYS = 90
WARNING_DAYS = 75

KEYS = [
    {"name": "币安API Key", "env_var": "BINANCE_API_KEY", "exchange": "binance", "permissions": "读取+交易"},
    {"name": "币安API Secret", "env_var": "BINANCE_API_SECRET", "exchange": "binance", "permissions": "读取+交易"},
    {"name": "火币API Key", "env_var": "HTX_API_KEY", "exchange": "htx", "permissions": "读取+交易"},
    {"name": "火币API Secret", "env_var": "HTX_API_SECRET", "exchange": "htx", "permissions": "读取+交易"},
    {"name": "欧易API Key", "env_var": "OKX_API_KEY", "exchange": "okx", "permissions": "读取+交易"},
    {"name": "欧易API Secret", "env_var": "OKX_API_SECRET", "exchange": "okx", "permissions": "读取+交易"},
    {"name": "DeepSeek API Key", "env_var": "DEEPSEEK_API_KEY", "exchange": "deepseek", "permissions": "LLM调用"},
    {"name": "Telegram Bot Token", "env_var": "TELEGRAM_BOT_TOKEN", "exchange": "telegram", "permissions": "消息推送"},
    {"name": "OANDA Token", "env_var": "FX_OANDA_TOKEN", "exchange": "oanda", "permissions": "Demo读取+交易"},
]


def _read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _log_event(event_type, message):
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": event_type,
        "source": "api_key_rotation",
        "message": message,
    }
    os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
    with open(EVENTS_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_rotation_log():
    return _read_json(ROTATION_LOG, {"rotations": []})


def get_key_age_days(key_name, rotation_log):
    """获取密钥自从上次轮换以来的天数"""
    rotations = rotation_log.get("rotations", [])
    key_rotations = [r for r in rotations if r.get("key_name") == key_name]
    if key_rotations:
        last_rotation = key_rotations[-1].get("date", "")
        try:
            last_date = time.strptime(last_rotation, "%Y-%m-%d")
            now = time.localtime()
            days = (time.mktime(now) - time.mktime(last_rotation and time.strptime(last_rotation, "%Y-%m-%d") or time.localtime())) / 86400
            return int(days), last_rotation
        except Exception:
            pass
    return None, None


def check_keys():
    print("[密钥轮换] 开始检查...")
    rotation_log = load_rotation_log()
    results = []
    warning_count = 0
    critical_count = 0
    ok_count = 0

    for key_info in KEYS:
        name = key_info["name"]
        env_var = key_info["env_var"]
        
        # 检查密钥是否配置
        env_path = os.path.expanduser("~/.env")
        env = {}
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        env[k.strip()] = v.strip()

        is_configured = bool(env.get(env_var))
        age_days, last_rotation = get_key_age_days(name, rotation_log)

        if not is_configured:
            status = "NOT_CONFIGURED"
            severity = "INFO"
            action = "未配置，跳过"
        elif age_days is None:
            status = "NO_ROTATION_RECORD"
            severity = "WARNING"
            action = "从未记录轮换，建议立即记录当前日期或轮换"
            warning_count += 1
        elif age_days > ROTATION_DAYS:
            status = "OVERDUE"
            severity = "CRITICAL"
            action = f"已超{age_days}天未轮换（上限{ROTATION_DAYS}天），立即轮换！"
            critical_count += 1
        elif age_days > WARNING_DAYS:
            status = "APPROACHING"
            severity = "WARNING"
            action = f"已{age_days}天未轮换，{ROTATION_DAYS - age_days}天后到期"
            warning_count += 1
        else:
            status = "OK"
            severity = "OK"
            action = f"已{age_days}天，{ROTATION_DAYS - age_days}天后到期"
            ok_count += 1

        # 密钥脱敏显示
        key_value = env.get(env_var, "")
        masked = key_value[:4] + "****" + key_value[-4:] if len(key_value) > 8 else "****"

        results.append({
            "name": name,
            "env_var": env_var,
            "exchange": key_info["exchange"],
            "permissions": key_info["permissions"],
            "configured": is_configured,
            "masked_value": masked,
            "age_days": age_days,
            "last_rotation": last_rotation,
            "status": status,
            "severity": severity,
            "action": action,
        })

        icon = {"OK": "✓", "APPROACHING": "⚠", "OVERDUE": "✗", "NO_ROTATION_RECORD": "?", "NOT_CONFIGURED": "-"}.get(status, "?")
        print(f"  {icon} {name}: {status} — {action}")

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "date": time.strftime("%Y-%m-%d"),
        "rotation_period_days": ROTATION_DAYS,
        "warning_threshold_days": WARNING_DAYS,
        "total_keys": len(KEYS),
        "ok": ok_count,
        "warnings": warning_count,
        "critical": critical_count,
        "summary": f"{ok_count}正常 / {warning_count}警告 / {critical_count}过期",
        "keys": results,
    }

    _write_json(OUTPUT_FILE, report)

    if critical_count > 0 or warning_count > 0:
        alert = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "severity": "CRITICAL" if critical_count > 0 else "WARNING",
            "type": "api_key_rotation",
            "message": f"密钥轮换检查: {critical_count}个过期, {warning_count}个即将到期",
            "details": [r for r in results if r["status"] not in ("OK", "NOT_CONFIGURED")],
        }
        _write_json(ALERT_FILE, alert)
        _log_event("security.alert", f"密钥轮换: {alert['message']}")

    _log_event("security.audit", f"密钥轮换检查完成: {report['summary']}")
    print(f"\n[密钥轮换] 完成: {report['summary']}")
    return report


def record_rotation(key_name):
    """记录密钥轮换（手动执行后调用）"""
    log = load_rotation_log()
    entry = {
        "key_name": key_name,
        "date": time.strftime("%Y-%m-%d"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "operator": "manual",
    }
    log.setdefault("rotations", []).append(entry)
    log["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _write_json(ROTATION_LOG, log)
    _log_event("security.rotation", f"密钥轮换记录: {key_name}")
    print(f"[密钥轮换] 已记录: {key_name} 在 {entry['date']}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--record":
        record_rotation(sys.argv[2])
    else:
        check_keys()
