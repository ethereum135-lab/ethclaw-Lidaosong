#!/bin/bash
# ============================================================
# ZQ Web4.0 交易系统 — 全量备份脚本
# ============================================================
# 备份范围：
#   1. ZQ项目文件 (~/zq_web4_trading_system/，排除.git/__pycache__)
#   2. Hermes核心 (state.db, config.yaml, .env, SOUL.md)
#   3. Hermes技能 (skills/)、记忆 (memories/)、定时任务 (cron/)
#   4. Hermes聊天记录 (sessions/)
#   5. Python虚拟环境 (~/.hermes-env/)
#   6. 配置文件 (config/auth.json)
# 格式：tar.gz 单文件压缩
# 保留：本地3天，iCloud 7天
# ============================================================

set -e

DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_ROOT="/Users/lidaosong/zq_web4_trading_system"
HERMES_ROOT="$HOME/.hermes"
HERMES_ENV="$HOME/.hermes-env"
ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs"
BACKUP_FILENAME="ZQ_Full_${DATE}.tar.gz"
LOCAL_BACKUP_DIR="${PROJECT_ROOT}/backups"
ICLOUD_BACKUP_DIR="${ICLOUD_DIR}/ZQ_Backups"
TEMP_DIR="/tmp/zq_full_backup_${DATE}"
LOG_FILE="/tmp/zq_backup_full_${DATE}.log"

# 确保目录存在
mkdir -p "$TEMP_DIR"
mkdir -p "$LOCAL_BACKUP_DIR"
mkdir -p "$ICLOUD_BACKUP_DIR"

echo "=========================================" | tee "$LOG_FILE"
echo "☁️  ZQ 全量备份" | tee -a "$LOG_FILE"
echo "时间: $(date)" | tee -a "$LOG_FILE"
echo "文件: $BACKUP_FILENAME" | tee -a "$LOG_FILE"
echo "=========================================" | tee -a "$LOG_FILE"

# ==========================================
# 第1步：收集文件到临时目录
# ==========================================
echo "" | tee -a "$LOG_FILE"
echo "[1/3] 收集文件..." | tee -a "$LOG_FILE"

# 1a) ZQ项目
if [ -d "$PROJECT_ROOT" ]; then
  mkdir -p "$TEMP_DIR/zq_system"
  rsync -aq --exclude='.git' --exclude='__pycache__' --exclude='node_modules' \
    --exclude='backups' \
    "$PROJECT_ROOT/" "$TEMP_DIR/zq_system/"
  echo "  ✅ ZQ项目 ($(du -sh "$TEMP_DIR/zq_system" | awk '{print $1}'))" | tee -a "$LOG_FILE"
fi

# 1b) Hermes核心
if [ -d "$HERMES_ROOT" ]; then
  mkdir -p "$TEMP_DIR/hermes"
  
  # 核心配置
  for f in config.yaml .env SOUL.md; do
    [ -f "$HERMES_ROOT/$f" ] && cp "$HERMES_ROOT/$f" "$TEMP_DIR/hermes/" && echo "  ✅ hermes/$f" | tee -a "$LOG_FILE"
  done
  
  # state.db
  [ -f "$HERMES_ROOT/state.db" ] && cp "$HERMES_ROOT/state.db" "$TEMP_DIR/hermes/" && echo "  ✅ hermes/state.db ($(du -sh "$TEMP_DIR/hermes/state.db" | awk '{print $1}'))" | tee -a "$LOG_FILE"
  
  # skills
  if [ -d "$HERMES_ROOT/skills" ]; then
    mkdir -p "$TEMP_DIR/hermes/skills"
    cp -a "$HERMES_ROOT/skills/" "$TEMP_DIR/hermes/skills/"
    echo "  ✅ hermes/skills/ ($(du -sh "$TEMP_DIR/hermes/skills" | awk '{print $1}'))" | tee -a "$LOG_FILE"
  fi
  
  # memories
  if [ -d "$HERMES_ROOT/memories" ]; then
    mkdir -p "$TEMP_DIR/hermes/memories"
    cp -a "$HERMES_ROOT/memories/" "$TEMP_DIR/hermes/memories/"
    echo "  ✅ hermes/memories/" | tee -a "$LOG_FILE"
  fi
  
  # cron
  if [ -d "$HERMES_ROOT/cron" ]; then
    mkdir -p "$TEMP_DIR/hermes/cron"
    cp -a "$HERMES_ROOT/cron/" "$TEMP_DIR/hermes/cron/"
    echo "  ✅ hermes/cron/" | tee -a "$LOG_FILE"
  fi
  
  # sessions (最近30天，控制大小)
  if [ -d "$HERMES_ROOT/sessions" ]; then
    mkdir -p "$TEMP_DIR/hermes/sessions"
    find "$HERMES_ROOT/sessions" -maxdepth 1 -type f -name "*.db" -mtime -30 -exec cp {} "$TEMP_DIR/hermes/sessions/" \;
    echo "  ✅ hermes/sessions/ (最近30天)" | tee -a "$LOG_FILE"
  fi
fi

# 1c) venv
if [ -d "$HERMES_ENV" ]; then
  mkdir -p "$TEMP_DIR/hermes-env"
  rsync -aq --exclude='__pycache__' "$HERMES_ENV/" "$TEMP_DIR/hermes-env/"
  echo "  ✅ hermes-env ($(du -sh "$TEMP_DIR/hermes-env" | awk '{print $1}'))" | tee -a "$LOG_FILE"
fi

# 1d) ZQ配置文件 (config/auth.json等)
if [ -f "$PROJECT_ROOT/config/auth.json" ]; then
  mkdir -p "$TEMP_DIR/zq_config"
  cp "$PROJECT_ROOT/config/"*.json "$TEMP_DIR/zq_config/" 2>/dev/null || true
  echo "  ✅ ZQ配置 (auth.json等)" | tee -a "$LOG_FILE"
fi

# ==========================================
# 第2步：打包压缩
# ==========================================
echo "" | tee -a "$LOG_FILE"
echo "[2/3] 打包压缩为 tar.gz..." | tee -a "$LOG_FILE"

RAW_SIZE=$(du -sh "$TEMP_DIR" | awk '{print $1}')
echo "  原始大小: $RAW_SIZE" | tee -a "$LOG_FILE"

cd /tmp
tar -czf "$LOCAL_BACKUP_DIR/$BACKUP_FILENAME" -C /tmp "zq_full_backup_${DATE}" 2>/dev/null

COMPRESSED_SIZE=$(du -sh "$LOCAL_BACKUP_DIR/$BACKUP_FILENAME" | awk '{print $1}')
echo "  ✅ 压缩完成: $COMPRESSED_SIZE" | tee -a "$LOG_FILE"

# ==========================================
# 第3步：同步到 iCloud
# ==========================================
echo "" | tee -a "$LOG_FILE"
echo "[3/3] 同步到 iCloud..." | tee -a "$LOG_FILE"

cp "$LOCAL_BACKUP_DIR/$BACKUP_FILENAME" "$ICLOUD_BACKUP_DIR/"
echo "  ✅ iCloud: $ICLOUD_BACKUP_DIR/$BACKUP_FILENAME" | tee -a "$LOG_FILE"

# ==========================================
# 清理过期备份
# ==========================================
echo "" | tee -a "$LOG_FILE"
echo "🧹 清理过期备份..." | tee -a "$LOG_FILE"

# 本地保留3天
LOCAL_DELETED=$(find "$LOCAL_BACKUP_DIR" -maxdepth 1 -name "ZQ_Full_*.tar.gz" -type f -mtime +3 -exec rm -v {} \; 2>/dev/null | wc -l | tr -d ' ')
echo "  本地: 删除 $LOCAL_DELETED 个旧备份 (保留3天)" | tee -a "$LOG_FILE"

# iCloud保留7天
ICLOUD_DELETED=$(find "$ICLOUD_BACKUP_DIR" -maxdepth 1 -name "ZQ_Full_*.tar.gz" -type f -mtime +7 -exec rm -v {} \; 2>/dev/null | wc -l | tr -d ' ')
echo "  iCloud: 删除 $ICLOUD_DELETED 个旧备份 (保留7天)" | tee -a "$LOG_FILE"

# ==========================================
# 清理临时文件
# ==========================================
rm -rf "$TEMP_DIR"

# ==========================================
# 完成
# ==========================================
echo "" | tee -a "$LOG_FILE"
echo "=========================================" | tee -a "$LOG_FILE"
echo "✅ 备份完成！" | tee -a "$LOG_FILE"
echo "  本地: $LOCAL_BACKUP_DIR/$BACKUP_FILENAME ($COMPRESSED_SIZE)" | tee -a "$LOG_FILE"
echo "  iCloud: $ICLOUD_BACKUP_DIR/$BACKUP_FILENAME" | tee -a "$LOG_FILE"
echo "=========================================" | tee -a "$LOG_FILE"
