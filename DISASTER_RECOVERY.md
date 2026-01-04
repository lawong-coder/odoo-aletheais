# Odoo Disaster Recovery Guide

## Overview

This guide covers complete restoration of your Odoo production instance to a new VM in case of catastrophic failure. Follow these steps to recover from:
- Complete server loss
- Hardware failure
- Data center outage
- Ransomware/corruption requiring clean rebuild

**Recovery Time Objective (RTO):** ~30-60 minutes  
**Recovery Point Objective (RPO):** Last successful backup (daily at 2 AM)

## Quick Start Checklist

- [ ] New VM with Ubuntu/Debian Linux
- [ ] Root/sudo access
- [ ] Network connectivity
- [ ] Access to backup server (`rsync://nas:/odoo-aletheais-prod/`)
- [ ] Latest backup filename noted

## Prerequisites on New VM

### 1. System Requirements

**Minimum specs:**
- CPU: 2 cores
- RAM: 4GB
- Disk: 50GB+ (depending on your data size)
- OS: Ubuntu 20.04+ or Debian 11+

### 2. Install Docker and Docker Compose

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker installation
docker --version
docker compose version

# Test Docker
docker run hello-world
```

### 3. Install Required Tools

```bash
sudo apt-get install -y rsync curl wget vim
```

## Step-by-Step Recovery Process

### Step 1: Download Backup from Remote Server

```bash
# Create working directory
mkdir -p ~/odoo-restore
cd ~/odoo-restore

# List available backups
rsync rsync://nas:/odoo-aletheais-prod/

# Download the latest backup (replace with actual filename)
rsync -avzh --progress \
  rsync://nas:/odoo-aletheais-prod/odoo_backup_20260104_120000.tar.gz \
  ./

# Verify download
ls -lh odoo_backup_*.tar.gz
```

### Step 2: Extract Backup Archive

```bash
# Extract backup
tar xzf odoo_backup_20260104_120000.tar.gz

# Verify contents
ls -la odoo_backup_20260104_120000/
# Should see: database.dump, filestore.tar.gz, .env, config/, custom-addons/
```

### Step 3: Set Up Project Structure

```bash
# Create project directory
mkdir -p ~/aletheais-prod
cd ~/aletheais-prod

# Copy files from backup
BACKUP_DIR=~/odoo-restore/odoo_backup_20260104_120000

cp "$BACKUP_DIR/.env" .
cp -r "$BACKUP_DIR/config" .
cp -r "$BACKUP_DIR/custom-addons" .
mkdir -p addons tmp

# Create scripts directory
mkdir -p scripts
```

### Step 4: Create docker-compose.yml

```bash
cat > docker-compose.yml << 'EOF'
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
EOF
```

### Step 5: Review Configuration

```bash
# Review and update .env if needed
nano .env

# Important settings to verify/update:
# - POSTGRES_PASSWORD (keep original or update)
# - ODOO_ADMIN_PASSWD (consider changing for security)
# - HOST_HTTP_PORT (default: 8069, change if port conflict)
# - HOST_LONGPOLL_PORT (default: 8072)
# - Remove or comment out RSYNC_REMOTE (not needed immediately)
```

### Step 6: Start Database Container

```bash
# Start only the database first
docker compose up -d db

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 15

# Check database health
docker compose ps
docker compose logs db | tail -n 20
```

### Step 7: Restore Database

```bash
# Copy database dump into container
BACKUP_DIR=~/odoo-restore/odoo_backup_20260104_120000
DB_CONTAINER=$(docker compose ps -q db)

docker cp "$BACKUP_DIR/database.dump" ${DB_CONTAINER}:/tmp/restore.dump

# Drop and recreate database (if needed)
docker compose exec db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS postgres;" 2>/dev/null || true
docker compose exec db psql -U odoo -d postgres -c "CREATE DATABASE postgres OWNER odoo;"

# Restore database from dump
echo "Restoring database... (this may take several minutes)"
docker compose exec db pg_restore \
  -U odoo \
  -d postgres \
  --no-owner \
  --role=odoo \
  --verbose \
  /tmp/restore.dump

# Verify database restoration
docker compose exec db psql -U odoo -d postgres -c "\dt" | head -n 20
```

### Step 8: Restore Filestore

```bash
# Get the volume name
VOLUME_NAME=$(docker volume ls -q | grep odoo-filestore)
echo "Volume: $VOLUME_NAME"

# Restore filestore from backup
BACKUP_DIR=~/odoo-restore/odoo_backup_20260104_120000

docker run --rm \
  -v ${VOLUME_NAME}:/target \
  -v "${BACKUP_DIR}":/backup:ro \
  alpine tar xzf /backup/filestore.tar.gz -C /target

echo "✓ Filestore restored"
```

### Step 9: Start Odoo Service

```bash
# Start Odoo
docker compose up -d odoo

# Watch logs for startup
docker compose logs -f odoo

# Wait for "Odoo is running" message
# Press Ctrl+C to exit logs
```

### Step 10: Verify Installation

```bash
# Check all containers are running
docker compose ps

# Test Odoo is responding
curl -I http://localhost:8069

# Check Odoo version
docker compose logs odoo | grep "Odoo version"

# View recent logs
docker compose logs --tail=50 odoo
```

### Step 11: Access Odoo

```bash
# Get VM IP address
ip addr show | grep "inet " | grep -v 127.0.0.1

# Access Odoo in browser:
# http://<vm-ip>:8069
# or if on same machine:
# http://localhost:8069
```

## Post-Recovery Checklist

### Immediate Verification (First 30 minutes)

- [ ] Odoo web interface loads successfully
- [ ] Can log in with admin credentials
- [ ] Database shows correct data
- [ ] Custom modules are installed and active
- [ ] File attachments are accessible
- [ ] No errors in docker logs

### Configuration Updates (First hour)

- [ ] Update DNS records to point to new VM IP
- [ ] Update firewall rules if needed
- [ ] Configure SSL/TLS certificates (if using reverse proxy)
- [ ] Update `.env` with new ODOO_ADMIN_PASSWD
- [ ] Set up backup configuration (RSYNC_REMOTE)
- [ ] Test backup script runs successfully

### Application Testing (First 2 hours)

- [ ] Test user logins across different roles
- [ ] Verify all installed modules work
- [ ] Test creating/editing records
- [ ] Test file uploads/downloads
- [ ] Verify reports generate correctly
- [ ] Test email functionality
- [ ] Verify scheduled actions run
- [ ] Check API integrations (if any)

### External Integrations (As needed)

- [ ] Reconfigure payment gateway connections
- [ ] Update API endpoints in external systems
- [ ] Reconfigure SMTP settings
- [ ] Update webhook URLs
- [ ] Test third-party integrations
- [ ] Update backup destinations

### Documentation Updates

- [ ] Document new VM IP address
- [ ] Update infrastructure documentation
- [ ] Record any configuration changes made
- [ ] Update disaster recovery runbook with lessons learned

## Automated Recovery Script

For faster recovery, use this automated script:

```bash
# Create the script
cat > ~/restore-odoo.sh << 'SCRIPT'
#!/bin/bash
set -e

# Configuration
BACKUP_FILE="$1"
PROJECT_NAME="aletheais-prod"
PROJECT_DIR="$HOME/$PROJECT_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Odoo Disaster Recovery Script${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Check backup file
if [ -z "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not specified${NC}"
    echo "Usage: $0 <backup_archive.tar.gz>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}Backup file: $BACKUP_FILE${NC}"
echo ""

# Extract backup
echo "Step 1/9: Extracting backup..."
TEMP_DIR=$(mktemp -d)
tar xzf "$BACKUP_FILE" -C "$TEMP_DIR"
BACKUP_NAME=$(basename "$BACKUP_FILE" .tar.gz)
BACKUP_PATH="$TEMP_DIR/$BACKUP_NAME"
echo -e "${GREEN}✓ Backup extracted${NC}"

# Create project structure
echo "Step 2/9: Setting up project structure..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

cp "$BACKUP_PATH/.env" .
cp -r "$BACKUP_PATH/config" .
cp -r "$BACKUP_PATH/custom-addons" .
mkdir -p addons tmp scripts
echo -e "${GREEN}✓ Project structure created${NC}"

# Create docker-compose.yml
echo "Step 3/9: Creating docker-compose.yml..."
cat > docker-compose.yml << 'EOF'
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
      test: ["CMD-SHELL", "pg_isready -U \${POSTGRES_USER} -d \${POSTGRES_DB}"]
      interval: 5s
      timeout: 3s
      retries: 20

  odoo:
    image: odoo:\${ODOO_VERSION}
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
      - "\${HOST_HTTP_PORT}:8069"
      - "\${HOST_LONGPOLL_PORT}:8072"

volumes:
  db-data:
  odoo-filestore:
EOF
echo -e "${GREEN}✓ docker-compose.yml created${NC}"

# Start database
echo "Step 4/9: Starting database container..."
docker compose up -d db
sleep 15
echo -e "${GREEN}✓ Database container started${NC}"

# Restore database
echo "Step 5/9: Restoring database..."
DB_CONTAINER=$(docker compose ps -q db)
docker cp "$BACKUP_PATH/database.dump" ${DB_CONTAINER}:/tmp/restore.dump

# Load environment
source .env
docker compose exec db psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB;" 2>/dev/null || true
docker compose exec db psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;"
docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --role="$POSTGRES_USER" /tmp/restore.dump 2>&1 | grep -v "ERROR.*already exists" || true
echo -e "${GREEN}✓ Database restored${NC}"

# Restore filestore
echo "Step 6/9: Restoring filestore..."
VOLUME_NAME="${PROJECT_NAME}_odoo-filestore"
docker run --rm \
  -v ${VOLUME_NAME}:/target \
  -v "$BACKUP_PATH":/backup:ro \
  alpine tar xzf /backup/filestore.tar.gz -C /target
echo -e "${GREEN}✓ Filestore restored${NC}"

# Start Odoo
echo "Step 7/9: Starting Odoo..."
docker compose up -d odoo
sleep 10
echo -e "${GREEN}✓ Odoo started${NC}"

# Wait for Odoo to be ready
echo "Step 8/9: Waiting for Odoo to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:${HOST_HTTP_PORT:-8069} > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Odoo is responding${NC}"
        break
    fi
    sleep 2
done

# Cleanup
echo "Step 9/9: Cleaning up..."
rm -rf "$TEMP_DIR"
echo -e "${GREEN}✓ Cleanup complete${NC}"

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Recovery Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Project location: $PROJECT_DIR"
echo "Access Odoo at: http://localhost:${HOST_HTTP_PORT:-8069}"
echo ""
echo "Next steps:"
echo "1. Test Odoo access in browser"
echo "2. Verify data integrity"
echo "3. Update DNS records"
echo "4. Configure backups"
echo ""
SCRIPT

chmod +x ~/restore-odoo.sh
```

**Usage:**
```bash
# Download backup
rsync -avzh rsync://nas:/odoo-aletheais-prod/odoo_backup_20260104_120000.tar.gz ~/

# Run restore script
~/restore-odoo.sh ~/odoo_backup_20260104_120000.tar.gz
```

## Troubleshooting

### Database Container Won't Start

```bash
# Check logs
docker compose logs db

# Common issues:
# - Port 5432 already in use
# - Insufficient disk space
# - Permission issues

# Solution: Check ports and disk space
sudo netstat -tulpn | grep 5432
df -h
```

### Database Restore Fails

```bash
# Check PostgreSQL version compatibility
docker compose exec db psql -U odoo -d postgres -c "SELECT version();"

# If version mismatch, update POSTGRES image version in docker-compose.yml
# Verify database dump
file ~/odoo-restore/odoo_backup_*/database.dump

# Manual restore with verbose output
docker compose exec db pg_restore \
  -U odoo -d postgres \
  --verbose \
  --no-owner \
  /tmp/restore.dump
```

### Odoo Won't Start

```bash
# Check logs
docker compose logs odoo

# Common issues:
# - Database connection failed
# - Module dependency issues
# - Configuration errors

# Verify database connectivity
docker compose exec odoo psql -h db -U odoo -d postgres -c "SELECT 1;"

# Check config file syntax
cat config/odoo.conf

# Try starting in shell mode
docker compose run --rm odoo odoo shell -d postgres
```

### Port Conflicts

```bash
# Check what's using the port
sudo netstat -tulpn | grep 8069

# Update .env with different port
nano .env
# Change HOST_HTTP_PORT=8070

# Restart services
docker compose down
docker compose up -d
```

### Missing Custom Modules

```bash
# Verify custom-addons directory
ls -la custom-addons/

# Update module list in Odoo
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d postgres -u all --stop-after-init

# Restart Odoo
docker compose restart odoo
```

### Filestore Not Working

```bash
# Check volume exists
docker volume ls | grep filestore

# Verify filestore contents
docker run --rm -v aletheais-prod_odoo-filestore:/data alpine ls -la /data

# Check permissions
docker compose exec odoo ls -la /var/lib/odoo
```

## Testing Your DR Plan

Regularly test your disaster recovery process:

### Quarterly DR Test (Recommended)

1. **Spin up test VM**
2. **Download latest backup**
3. **Follow recovery steps**
4. **Document time taken**
5. **Note any issues**
6. **Update procedures**
7. **Destroy test VM**

### DR Test Checklist

- [ ] Test VM provisioning time
- [ ] Backup download speed
- [ ] Database restore time
- [ ] Application startup time
- [ ] Functionality verification
- [ ] Total recovery time
- [ ] Issues encountered
- [ ] Documentation gaps

## Contact Information

**In case of emergency:**
- System Administrator: [Your contact]
- Backup Server Admin: [Your contact]
- Cloud Provider Support: [Support contact]

**Important URLs:**
- Backup Server: rsync://nas:/odoo-aletheais-prod/
- Production Odoo: http://[production-ip]:8069
- Documentation: /home/chirpydog/services/aletheais-prod/

**Backup Schedule:**
- Frequency: Daily at 2:00 AM UTC
- Retention: 7 days local, 30 days remote
- Location: rsync://nas:/odoo-aletheais-prod/

## Additional Resources

- [BACKUP.md](BACKUP.md) - Regular backup procedures
- [Odoo Documentation](https://www.odoo.com/documentation/18.0/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
