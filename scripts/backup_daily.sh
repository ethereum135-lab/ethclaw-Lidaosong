#!/bin/bash
# ZQ交易系统每日备份到iCloud
# 方法参考人生导师的Hermes备份方案（已验证可行）

DATE=$(date +%Y%m%d_%H%M%S)
ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs"
BACKUP_NAME="ZQ_Backup_$DATE"
BACKUP_DIR="$ICLOUD_DIR/$BACKUP_NAME"
LOG_FILE="/tmp/zq_backup_${DATE}.log"

echo "=========================================" | tee "$LOG_FILE"
echo "☁️  ZQ交易系统备份到iCloud" | tee -a "$LOG_FILE"
echo "时间: $(date)" | tee -a "$LOG_FILE"
echo "备份: $BACKUP_DIR" | tee -a "$LOG_FILE"
echo "=========================================" | tee -a "$LOG_FILE"

# 创建目录（直接在iCloud Drive里创建，不要从别处move）
mkdir -p "$BACKUP_DIR"

# 1. 备份项目
echo "" | tee -a "$LOG_FILE"
echo "[1/2] 备份项目文件..." | tee -a "$LOG_FILE"
rsync -aq --exclude='.git' --exclude='__pycache__' --exclude='node_modules' \
  /Users/lidaosong/zq_web4_trading_system/ "${BACKUP_DIR}/project/"
echo "  ✅ project/ ($(du -sh /Users/lidaosong/zq_web4_trading_system | awk '{print $1}'))" | tee -a "$LOG_FILE"

# 2. 备份关键配置和记忆
echo "" | tee -a "$LOG_FILE"
echo "[2/2] 备份配置/记忆/技能..." | tee -a "$LOG_FILE"
for d in config memories skills; do
  if [ -d "/Users/lidaosong/zq_web4_trading_system/$d" ]; then
    mkdir -p "$BACKUP_DIR/$d"
    cp -a "/Users/lidaosong/zq_web4_trading_system/$d/" "$BACKUP_DIR/$d/"
    echo "  ✅ $d/" | tee -a "$LOG_FILE"
  fi
done

# 备份清单
echo "ZQ Trading System Backup — $(date)" > "$BACKUP_DIR/备份清单.txt"

# 一键恢复
cat > "$BACKUP_DIR/一键恢复.sh" << 'EOF'
#!/bin/bash
echo "Restoring ZQ System..."
rsync -aq project/ ~/zq_web4_trading_system/
for d in config memories skills; do
  [ -d "$d" ] && cp -a "$d/" ~/zq_web4_trading_system/$d/
done
echo "Done."
EOF
chmod +x "$BACKUP_DIR/一键恢复.sh"

echo "" | tee -a "$LOG_FILE"
echo "📦 大小: $(du -sh "$BACKUP_DIR" | awk '{print $1}')" | tee -a "$LOG_FILE"

# 保留最近7天的备份，清理更旧的
echo "" | tee -a "$LOG_FILE"
echo "🧹 清理7天前备份..." | tee -a "$LOG_FILE"
find "$ICLOUD_DIR" -maxdepth 1 -name "ZQ_Backup_*" -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null
echo "  ✅ 清理完成" | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "=========================================" | tee -a "$LOG_FILE"
echo "✅ 备份完成！" | tee -a "$LOG_FILE"
echo "位置: $BACKUP_DIR" | tee -a "$LOG_FILE"
echo "=========================================" | tee -a "$LOG_FILE"
