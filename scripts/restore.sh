#!/bin/bash

# Odoo Production Restore Script
# Restores PostgreSQL database and Odoo filestore from backup

set -e  # Exit on error

# Usage function
usage() {
    echo "Usage: $0 <backup_archive.tar.gz>"
    echo "Example: $0 /tmp/odoo-backups/odoo_backup_20260104_120000.tar.gz"
    exit 1
}

# Check if backup file is provided
if [ -z "$1" ]; then
    usage
fi

BACKUP_ARCHIVE="$1"

if [ ! -f "$BACKUP_ARCHIVE" ]; then
    echo "Error: Backup file not found: $BACKUP_ARCHIVE"
    exit 1
fi

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_DIR}/.env"

if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "Error: .env file not found at $ENV_FILE"
    exit 1
fi

RESTORE_DIR="/tmp/odoo-restore-$$"

echo "==================================="
echo "Odoo Production Restore - $(date)"
echo "==================================="
echo "Backup: $BACKUP_ARCHIVE"
echo ""

# Confirmation prompt
read -p "⚠️  This will REPLACE your current database and filestore. Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Extract backup archive
echo "Extracting backup archive..."
mkdir -p "$RESTORE_DIR"
tar xzf "$BACKUP_ARCHIVE" -C "$RESTORE_DIR"
BACKUP_NAME=$(basename "$BACKUP_ARCHIVE" .tar.gz)
BACKUP_PATH="${RESTORE_DIR}/${BACKUP_NAME}"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "Error: Backup directory not found in archive"
    rm -rf "$RESTORE_DIR"
    exit 1
fi

echo "✓ Archive extracted"

# Stop Odoo service (keep database running)
echo "Stopping Odoo service..."
docker compose -f "${PROJECT_DIR}/docker-compose.yml" stop odoo
echo "✓ Odoo stopped"

# 1. Restore Database
echo "Restoring database..."
# Drop existing database
docker exec $(docker compose -f "${PROJECT_DIR}/docker-compose.yml" ps -q db) \
    psql -U "$POSTGRES_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB';" || true

docker exec $(docker compose -f "${PROJECT_DIR}/docker-compose.yml" ps -q db) \
    psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB;" || true

docker exec $(docker compose -f "${PROJECT_DIR}/docker-compose.yml" ps -q db) \
    psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;"

# Restore from dump
docker exec -i $(docker compose -f "${PROJECT_DIR}/docker-compose.yml" ps -q db) \
    pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --role="$POSTGRES_USER" \
    < "${BACKUP_PATH}/database.dump"

echo "✓ Database restored"

# 2. Restore Filestore
echo "Restoring filestore..."
# Clear existing filestore
docker run --rm \
    -v aletheais-prod_odoo-filestore:/target \
    alpine sh -c "rm -rf /target/* /target/.*" 2>/dev/null || true

# Extract filestore backup
docker run --rm \
    -v aletheais-prod_odoo-filestore:/target \
    -v "${BACKUP_PATH}":/backup:ro \
    alpine tar xzf /backup/filestore.tar.gz -C /target

echo "✓ Filestore restored"

# 3. Restore custom addons (optional)
if [ -d "${BACKUP_PATH}/custom-addons" ]; then
    echo "Restoring custom addons..."
    rsync -a --delete "${BACKUP_PATH}/custom-addons/" "${PROJECT_DIR}/custom-addons/"
    echo "✓ Custom addons restored"
fi

# Start Odoo service
echo "Starting Odoo service..."
docker compose -f "${PROJECT_DIR}/docker-compose.yml" start odoo
echo "✓ Odoo started"

# Cleanup
echo "Cleaning up temporary files..."
rm -rf "$RESTORE_DIR"

echo ""
echo "==================================="
echo "Restore Summary"
echo "==================================="
echo "Status: ✓ SUCCESS"
echo "Odoo is now running with restored data"
echo "Access: http://localhost:${HOST_HTTP_PORT}"
echo "==================================="
