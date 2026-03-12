#!/bin/bash

set -euo pipefail

# Upgrade an Odoo module in the running Odoo container.
# Defaults are set for this project but can be overridden via arguments.
# Usage:
#   ./scripts/upgrade_sale_order_label_override.sh
#   ./scripts/upgrade_sale_order_label_override.sh <database> <module>

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DB_NAME="${1:-aletheais}"
MODULE_NAME="${2:-sale_order_label_override}"
CONTAINER_NAME="aletheais-prod-odoo-1"

cd "$PROJECT_DIR"

echo "Upgrading module '$MODULE_NAME' on database '$DB_NAME'..."
docker exec "$CONTAINER_NAME" odoo -d "$DB_NAME" -u "$MODULE_NAME" --stop-after-init

echo "Upgrade complete."
