# Odoo Production Backup Guide

## Overview
This backup solution provides automated backups of your Odoo production instance to a remote rsync server.

**What gets backed up:**
- PostgreSQL database (full dump)
- Odoo filestore (attachments, media files)
- Configuration files (.env, odoo.conf)
- Custom addons

## Setup Instructions

### 1. Configure Remote Rsync Server

Edit your `.env` file and add your rsync server details:

```bash
# Backup Configuration (rsync daemon protocol)
RSYNC_REMOTE=rsync://nas:/odoo-aletheais-prod/
```

**Note:** This uses rsync daemon protocol (no SSH required). If your rsync server requires authentication, you can add credentials in `~/.netrc` or use environment variables.

### 2. Make Scripts Executable

```bash
chmod +x scripts/backup.sh
chmod +x scripts/restore.sh
chmod +x scripts/setup-cron.sh
```

### 3. Test Manual Backup

Run a test backup:

```bash
./scripts/backup.sh
```

This will:
- Dump the PostgreSQL database
- Archive the Odoo filestore
- Copy configuration and custom addons
- Create a compressed archive in `<project-root>/tmp/`
- Sync to your remote rsync server

### 4. Set Up Automated Backups

To schedule daily backups at 2:00 AM:

```bash
./scripts/setup-cron.sh
```

**Custom schedules:** Edit crontab directly:
```bash
crontab -e
```

Example schedules:
- `0 2 * * *` - Daily at 2:00 AM (default)
- `0 */6 * * *` - Every 6 hours
- `0 0 * * 0` - Weekly on Sunday at midnight
- `0 3 * * 1-5` - Weekdays at 3:00 AM

## Manual Operations

### Manual Backup
```bash
cd /home/chirpydog/services/aletheais-prod
./scripts/backup.sh
```

### Restore from Backup
```bash
./scripts/restore.sh /home/chirpydog/services/aletheais-prod/tmp/odoo_backup_20260104_120000.tar.gz
```

⚠️ **Warning:** Restore will replace your current database and filestore.

### Download Backup from Remote Server
```bash
rsync -avzh \
  rsync://nas:/odoo-aletheais-prod/odoo_backup_20260104_120000.tar.gz \
  ./tmp/
```

### List Remote Backups
```bash
rsync rsync://nas:/odoo-aletheais-prod/
```

## Disaster Recovery (Restore to New VM)

If you need to restore your Odoo instance to a completely different VM (disaster recovery scenario), follow these steps:

### Prerequisites on New VM

1. **Install Docker and Docker Compose:**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose (if not included)
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

2. **Download backup from remote server:**
```bash
mkdir -p ~/odoo-restore
cd ~/odoo-restore

# Download the backup
rsync -avzh \
  rsync://nas:/odoo-aletheais-prod/odoo_backup_20260104_120000.tar.gz \
  ./
```

3. **Extract backup archive:**
```bash
tar xzf odoo_backup_20260104_120000.tar.gz
cd odoo_backup_20260104_120000
```

### Restore Steps

**1. Create project structure:**
```bash
mkdir -p ~/aletheais-prod
cd ~/aletheais-prod

# Copy essential files from backup
cp ~/odoo-restore/odoo_backup_20260104_120000/.env .
cp ~/odoo-restore/odoo_backup_20260104_120000/docker-compose.yml . 2>/dev/null || true
cp -r ~/odoo-restore/odoo_backup_20260104_120000/config .
cp -r ~/odoo-restore/odoo_backup_20260104_120000/custom-addons .
mkdir -p addons
```

**2. Create docker-compose.yml** (if not in backup):
```yaml
services:
  db:
    image: postgres:15
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 3s
      retries: 20

  odoo:
    image: odoo:${ODOO_VERSION}
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    env_file: .env
    command: >
      odoo -c /etc/odoo/odoo.conf
           --db-filter=.*
    volumes:
      - ./config/odoo.conf:/etc/odoo/odoo.conf:ro
      - ./addons:/mnt/odoo/addons
      - ./custom-addons:/mnt/odoo/custom-addons
      - odoo-filestore:/var/lib/odoo
    ports:
      - "${HOST_HTTP_PORT}:8069"
      - "${HOST_LONGPOLL_PORT}:8072"

volumes:
  db-data:
  odoo-filestore:
```

**3. Review and update .env file:**
```bash
nano .env
# Update if needed:
# - HOST_HTTP_PORT (if port 8069 is taken)
# - ODOO_ADMIN_PASSWD (change for security)
# - Remove RSYNC_REMOTE (not needed yet)
```

**4. Start containers:**
```bash
docker compose up -d
# Wait for containers to be healthy
docker compose ps
```

**5. Restore database:**
```bash
# Copy database dump into running container
docker cp ~/odoo-restore/odoo_backup_20260104_120000/database.dump \
  $(docker compose ps -q db):/tmp/

# Restore database
docker compose exec db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS postgres;"
docker compose exec db psql -U odoo -d postgres -c "CREATE DATABASE postgres OWNER odoo;"
docker compose exec db pg_restore -U odoo -d postgres --no-owner --role=odoo /tmp/database.dump
```

**6. Restore filestore:**
```bash
# Stop Odoo temporarily
docker compose stop odoo

# Restore filestore
docker run --rm \
  -v $(docker volume inspect --format '{{ .Mountpoint }}' aletheais-prod_odoo-filestore):/target \
  -v ~/odoo-restore/odoo_backup_20260104_120000:/backup:ro \
  alpine tar xzf /backup/filestore.tar.gz -C /target

# Restart Odoo
docker compose start odoo
```

**7. Verify restoration:**
```bash
# Check logs
docker compose logs -f odoo

# Access Odoo
curl http://localhost:8069
# Or open in browser: http://<new-vm-ip>:8069
```

### Post-Recovery Checklist

- [ ] Verify database is accessible
- [ ] Check that all custom modules are working
- [ ] Test file attachments/uploads
- [ ] Update DNS records if needed
- [ ] Reconfigure backup script with new paths
- [ ] Test user logins
- [ ] Verify integrations (email, payment gateways, etc.)
- [ ] Update SSL certificates if applicable
- [ ] Review and update firewall rules

### Alternative: Quick Restore Script

Create `quick-restore.sh` on the new VM:

```bash
#!/bin/bash
set -e

BACKUP_FILE="$1"
PROJECT_DIR="$HOME/aletheais-prod"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_archive.tar.gz>"
    exit 1
fi

echo "Extracting backup..."
TEMP_DIR=$(mktemp -d)
tar xzf "$BACKUP_FILE" -C "$TEMP_DIR"
BACKUP_NAME=$(basename "$BACKUP_FILE" .tar.gz)
BACKUP_PATH="$TEMP_DIR/$BACKUP_NAME"

echo "Setting up project..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

cp "$BACKUP_PATH/.env" .
cp -r "$BACKUP_PATH/config" .
cp -r "$BACKUP_PATH/custom-addons" .
mkdir -p addons

# Create docker-compose.yml if needed
if [ ! -f docker-compose.yml ]; then
    echo "Create docker-compose.yml manually or copy from backup"
    exit 1
fi

echo "Starting containers..."
docker compose up -d db
sleep 10

echo "Restoring database..."
docker cp "$BACKUP_PATH/database.dump" \
  $(docker compose ps -q db):/tmp/restore.dump
docker compose exec db pg_restore -U odoo -d postgres --no-owner --role=odoo \
  /tmp/restore.dump || true

echo "Restoring filestore..."
docker run --rm \
  -v aletheais-prod_odoo-filestore:/target \
  -v "$BACKUP_PATH":/backup:ro \
  alpine tar xzf /backup/filestore.tar.gz -C /target

echo "Starting Odoo..."
docker compose up -d

rm -rf "$TEMP_DIR"
echo "Restore complete! Access at http://localhost:8069"
```

## Backup File Structure

Each backup creates a timestamped archive:
```
odoo_backup_20260104_120000.tar.gz
├── database.dump          # PostgreSQL binary dump
├── filestore.tar.gz       # Odoo filestore (attachments)
├── .env                   # Environment configuration
├── config/                # Odoo configuration
│   ├── odoo.conf
│   └── odoo.conf.sample
├── custom-addons/         # Your custom modules
│   ├── website_footer_override/
│   └── sale_order_label_override/
└── backup_info.txt        # Backup metadata
```

## Monitoring & Maintenance

### Check Backup Logs
```bash
tail -f /var/log/odoo-backup.log
```

### Check Last Backup
```bash
ls -lh tmp/ | tail -n 5
```

### Verify Remote Backups
```bash
rsync rsync://nas:/odoo-aletheais-prod/
```

### Local Retention
By default, local backups are kept for 7 days. Modify `RETENTION_DAYS` in [scripts/backup.sh](scripts/backup.sh) to change this.

## Remote Server Setup (For Reference)

### Rsync Daemon Configuration

On your NAS or backup server, configure the rsync daemon. Edit `/etc/rsyncd.conf`:

```ini
[odoo-aletheais-prod]
    path = /backups/odoo-aletheais-prod
    comment = Odoo production backups
    uid = backup
    gid = backup
    read only = no
    list = yes
    # Optional authentication:
    # auth users = odoo-backup
    # secrets file = /etc/rsyncd.secrets
```

Create backup directory:
```bash
sudo mkdir -p /backups/odoo-aletheais-prod
sudo useradd -m backup
sudo chown backup:backup /backups/odoo-aletheais-prod
```

Restart rsync daemon:
```bash
sudo systemctl restart rsync
# or
sudo systemctl restart rsyncd
```

### Optional: Set up remote retention policy

On the backup server, create cleanup script:

```bash
#!/bin/bash
find /backups/odoo-aletheais-prod -name "odoo_backup_*.tar.gz" -type f -mtime +30 -delete
```

Add to crontab:
```bash
0 4 * * * /usr/local/bin/cleanup-odoo-backups.sh
```

## Troubleshooting

### Backup fails: "RSYNC_REMOTE not set"
Configure `RSYNC_REMOTE=rsync://nas:/odoo-aletheais-prod/` in your `.env` file.

### Rsync connection fails
- Verify rsync daemon is running: `sudo systemctl status rsync`
- Test connection: `rsync rsync://nas:/odoo-aletheais-prod/`
- Check firewall allows port 873 (rsync default)
- If using authentication, verify credentials

### Database backup fails
- Ensure PostgreSQL container is running: `docker compose ps`
- Check database credentials in `.env`
- Verify disk space: `df -h`

### Filestore backup fails
- Check Docker volume exists: `docker volume ls | grep filestore`
- Verify permissions on backup directory

### Restore fails
- Ensure backup file exists and is valid: `tar tzf backup.tar.gz`
- Check that database container is running
- Verify you have sufficient disk space

## Security Recommendations

1. **Encrypt backups:** Consider encrypting sensitive data before rsync
2. **Network security:** Use VPN or restrict rsync daemon access by IP
3. **Authentication:** Enable rsync daemon authentication if needed
4. **Test restores:** Regularly test restore process in non-production environment
5. **Monitor backups:** Set up alerts if backups fail

## Additional Options

### Encrypt Backups Before Syncing

Add to [scripts/backup.sh](scripts/backup.sh) before rsync:
```bash
# Encrypt backup
gpg --symmetric --cipher-algo AES256 "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
# Then sync the .gpg file instead
rsync -avzh --progress "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz.gpg" "${RSYNC_REMOTE}"
```

### Backup to Multiple Locations

Modify [scripts/backup.sh](scripts/backup.sh) to sync to multiple servers:
```bash
for REMOTE in "rsync://nas1:/odoo-backups/" "rsync://nas2:/odoo-backups/"; do
    rsync -avzh "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" "${REMOTE}"
done
```

## Questions?

For issues or questions, check:
- Logs: `/var/log/odoo-backup.log`
- Docker logs: `docker compose logs`
- Disk space: `df -h`
- Backup directory: `ls -lh tmp/`
