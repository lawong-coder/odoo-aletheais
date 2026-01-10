#!/bin/bash

# Odoo Production Backup Script
# Backs up PostgreSQL database and Odoo filestore to remote rsync server
set -x
set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/tmp"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="odoo_aletheais_prod_backup_${TIMESTAMP}"
RETENTION_DAYS=7  # Local backup retention

# Load environment variables
ENV_FILE="${PROJECT_DIR}/.env"

if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "Error: .env file not found at $ENV_FILE"
    exit 1
fi

# Rsync remote server configuration (using rsync daemon protocol)
# Set in your .env file: RSYNC_REMOTE=rsync://nas:/odoo-aletheais-prod/

# Validate rsync configuration
if [ -z "$RSYNC_REMOTE" ]; then
    echo "Error: RSYNC_REMOTE not set in .env file"
    echo "  Example: RSYNC_REMOTE=rsync://nas:/odoo-aletheais-prod/"
    exit 1
fi

echo "==================================="
echo "Odoo Production Backup - $(date)"
echo "==================================="

# Create backup directory
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# 1. Backup PostgreSQL Database
echo "Backing up PostgreSQL database..."
docker exec $(docker compose -f "${PROJECT_DIR}/docker-compose.yml" ps -q db) \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c -b \
    > "${BACKUP_DIR}/${BACKUP_NAME}/database.dump"

if [ $? -eq 0 ]; then
    echo "✓ Database backup completed"
else
    echo "✗ Database backup failed"
    exit 1
fi

# 2. Backup Odoo Filestore (attachments, etc.)
echo "Backing up Odoo filestore..."
docker run --rm \
    -v "$(docker volume inspect --format '{{ .Mountpoint }}' aletheais-prod_odoo-filestore 2>/dev/null || echo 'aletheais-prod_odoo-filestore')":/source:ro \
    -v "${BACKUP_DIR}/${BACKUP_NAME}":/backup \
    alpine tar czf /backup/filestore.tar.gz -C /source .

if [ $? -eq 0 ]; then
    echo "✓ Filestore backup completed"
else
    echo "✗ Filestore backup failed"
    exit 1
fi

# 3. Backup configuration files
echo "Backing up configuration..."
cp "${PROJECT_DIR}/.env" "${BACKUP_DIR}/${BACKUP_NAME}/.env"
cp -r "${PROJECT_DIR}/config" "${BACKUP_DIR}/${BACKUP_NAME}/"
cp -r "${PROJECT_DIR}/custom-addons" "${BACKUP_DIR}/${BACKUP_NAME}/"

# Create backup metadata
cat > "${BACKUP_DIR}/${BACKUP_NAME}/backup_info.txt" << EOF
Backup Date: $(date)
Database: $POSTGRES_DB
Odoo Version: $ODOO_VERSION
Backup Type: Full (Database + Filestore + Config + Custom Addons)
EOF

echo "✓ Configuration backup completed"

# 4. Create compressed archive
echo "Creating compressed archive..."
cd "$BACKUP_DIR"
tar czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

echo "✓ Archive created: ${BACKUP_NAME}.tar.gz"

# 5. Sync to remote rsync server
echo "Syncing to remote server..."

rsync -avzh --progress \
    "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" \
    "${RSYNC_REMOTE}"

if [ $? -eq 0 ]; then
    echo "✓ Backup synced to remote server: ${RSYNC_REMOTE}"
else
    echo "✗ Remote sync failed"
    exit 1
fi

# 6. Cleanup old local backups (keep last N days)
echo "Cleaning up old local backups..."
find "$BACKUP_DIR" -name "odoo_backup_*.tar.gz" -type f -mtime +${RETENTION_DAYS} -delete
echo "✓ Cleanup completed (retained last ${RETENTION_DAYS} days)"

# Display backup summary
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
echo ""
echo "==================================="
echo "Backup Summary"
echo "==================================="
echo "Backup file: ${BACKUP_NAME}.tar.gz"
echo "Size: ${BACKUP_SIZE}"
echo "Local: ${BACKUP_DIR}/"
echo "Remote: ${RSYNC_REMOTE}"
echo "Status: ✓ SUCCESS"
echo "==================================="
