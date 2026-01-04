#!/bin/bash

# Setup automated backup cron job

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="${SCRIPT_DIR}/backup.sh"

echo "Setting up automated backup cron job..."

# Make backup script executable
chmod +x "$BACKUP_SCRIPT"

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
    echo "Cron job already exists. Current crontab:"
    crontab -l | grep "$BACKUP_SCRIPT"
else
    # Add cron job (daily at 2 AM)
    (crontab -l 2>/dev/null; echo "0 2 * * * $BACKUP_SCRIPT >> /var/log/odoo-backup.log 2>&1") | crontab -
    echo "✓ Cron job added: Daily backup at 2:00 AM"
    echo "  Logs: /var/log/odoo-backup.log"
fi

echo ""
echo "Current crontab:"
crontab -l

echo ""
echo "To modify backup schedule, edit crontab with: crontab -e"
echo "Example schedules:"
echo "  0 2 * * *    - Daily at 2:00 AM"
echo "  0 */6 * * *  - Every 6 hours"
echo "  0 0 * * 0    - Weekly on Sunday at midnight"
