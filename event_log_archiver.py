#!/usr/bin/env python3
"""
事件日志自动归档器 (Event Log Archiver)
功能：将30天前的events.ndjson日志归档到压缩文件，释放空间
保留最近30天在events.ndjson，历史数据移至archive/

运行方式：
- Cron: 每日凌晨3:17执行
- 手动: python3 event_log_archiver.py
- 恢复: python3 event_log_archiver.py --restore 2026-09
"""
import json, os, sys, time, gzip
from datetime import datetime, timedelta

SC = "/home/ubuntu/shared_context"
EVENTS_FILE = os.path.join(SC, "events/events.ndjson")
ARCHIVE_DIR = os.path.join(SC, "events/archive/")
RETENTION_DAYS = 30
MAX_FILE_SIZE_MB = 50  # 超过50MB也触发归档


def read_events():
    if not os.path.exists(EVENTS_FILE):
        return []
    events = []
    with open(EVENTS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def should_archive(events):
    if not events:
        return False, "无事件"
    
    file_size = os.path.getsize(EVENTS_FILE) / (1024 * 1024) if os.path.exists(EVENTS_FILE) else 0
    if file_size > MAX_FILE_SIZE_MB:
        return True, f"文件{file_size:.1f}MB超过{MAX_FILE_SIZE_MB}MB"
    
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    old_count = sum(1 for e in events if _parse_ts(e.get("timestamp", "")) < cutoff)
    
    if old_count > 0:
        return True, f"{old_count}条事件超过{RETENTION_DAYS}天"
    return False, f"全部{len(events)}条事件在{RETENTION_DAYS}天内"


def _parse_ts(ts_str):
    try:
        return datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now()


def archive():
    events = read_events()
    should, reason = should_archive(events)
    
    if not should:
        print(f"[事件归档] 跳过: {reason}")
        return
    
    print(f"[事件归档] 触发: {reason}, 共{len(events)}条事件")
    
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    
    old_events = []
    new_events = []
    
    for e in events:
        if _parse_ts(e.get("timestamp", "")) < cutoff:
            old_events.append(e)
        else:
            new_events.append(e)
    
    if not old_events:
        print("[事件归档] 无需归档的事件")
        return
    
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    now = datetime.now()
    archive_name = f"events_{now.strftime('%Y%m%d')}_{now.strftime('%H%M%S')}"
    archive_path = os.path.join(ARCHIVE_DIR, f"{archive_name}.ndjson.gz")
    
    with gzip.open(archive_path, "wt", encoding="utf-8") as f:
        for e in old_events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    
    with open(EVENTS_FILE, "w") as f:
        for e in new_events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    
    archive_size = os.path.getsize(archive_path) / 1024
    
    summary = {
        "archive_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "archived_count": len(old_events),
        "remaining_count": len(new_events),
        "archive_file": archive_path,
        "archive_size_kb": round(archive_size, 1),
        "retention_days": RETENTION_DAYS,
    }
    
    summary_path = os.path.join(ARCHIVE_DIR, f"{archive_name}_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    _log_event("system.archive", f"事件日志归档: {len(old_events)}条→{archive_path} ({archive_size:.1f}KB)")
    
    print(f"[事件归档] 完成:")
    print(f"  归档: {len(old_events)}条 → {archive_path} ({archive_size:.1f}KB)")
    print(f"  保留: {len(new_events)}条 → {EVENTS_FILE}")
    print(f"  摘要: {summary_path}")


def restore(month_str):
    """恢复指定月份的归档日志"""
    found = False
    for fname in sorted(os.listdir(ARCHIVE_DIR)):
        if month_str in fname and fname.endswith(".ndjson.gz"):
            archive_path = os.path.join(ARCHIVE_DIR, fname)
            with gzip.open(archive_path, "rt", encoding="utf-8") as f:
                events = [json.loads(line) for line in f if line.strip()]
            
            output = os.path.join(ARCHIVE_DIR, f"restored_{month_str}_{fname.replace('.ndjson.gz', '.ndjson')}")
            with open(output, "w") as f:
                for e in events:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
            
            print(f"[事件恢复] {fname}: {len(events)}条 → {output}")
            found = True
    
    if not found:
        print(f"[事件恢复] 未找到 {month_str} 的归档")


def _log_event(event_type, message):
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": event_type,
        "source": "event_log_archiver",
        "message": message,
    }
    os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
    with open(EVENTS_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def status():
    """显示当前事件日志状态"""
    events = read_events()
    file_size = os.path.getsize(EVENTS_FILE) / (1024 * 1024) if os.path.exists(EVENTS_FILE) else 0
    
    by_type = {}
    for e in events:
        t = e.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    
    oldest = min((_parse_ts(e.get("timestamp", "")) for e in events), default=None)
    newest = max((_parse_ts(e.get("timestamp", "")) for e in events), default=None)
    
    archives = []
    if os.path.exists(ARCHIVE_DIR):
        archives = [f for f in os.listdir(ARCHIVE_DIR) if f.endswith(".ndjson.gz")]
    
    print(f"[事件日志状态]")
    print(f"  当前文件: {EVENTS_FILE}")
    print(f"  文件大小: {file_size:.2f} MB")
    print(f"  事件总数: {len(events)}")
    print(f"  最早事件: {oldest.strftime('%Y-%m-%d %H:%M') if oldest else '无'}")
    print(f"  最新事件: {newest.strftime('%Y-%m-%d %H:%M') if newest else '无'}")
    print(f"  归档文件: {len(archives)}个")
    print(f"  事件类型:")
    for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"    {t}: {c}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--restore":
            month = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m")
            restore(month)
        elif sys.argv[1] == "--status":
            status()
        elif sys.argv[1] == "--force":
            archive()
    else:
        archive()
