#!/usr/bin/env python3
"""
Quick Odoo dependency validator

How to execute:
1) With environment variables (recommended):
    export ODOO_URL=http://localhost:8069
    export ODOO_DB=aletheais
    export ODOO_USERNAME=admin@aletheais.com
    export ODOO_PASSWORD=your_password
    python3 scripts/validate_deps.py sale_order_label_override

2) With command-line arguments:
    python3 scripts/validate_deps.py sale_order_label_override \
         --url http://localhost:8069 \
         --db aletheais \
         --username admin@aletheais.com \
         --password your_password

Tip:
- Use --help to see all options: python3 scripts/validate_deps.py --help
"""

import xmlrpc.client
import ssl
import sys
import argparse
import os

def parse_args():
    """Parse CLI arguments for module validation."""
    # Example: python3 scripts/validate_deps.py sale_order_label_override
    parser = argparse.ArgumentParser(
        description='Validate Odoo module installation/dependencies via XML-RPC.'
    )
    parser.add_argument(
        'module',
        help='Technical module name to validate'
    )
    parser.add_argument('--url', default=None, help='Odoo base URL (or ODOO_URL)')
    parser.add_argument('--db', default=None, help='Database name (or ODOO_DB)')
    parser.add_argument('--username', default=None, help='Odoo username (or ODOO_USERNAME)')
    parser.add_argument('--password', default=None, help='Odoo password (or ODOO_PASSWORD)')

    args = parser.parse_args()

    # Precedence: CLI arg > environment variable > built-in default
    args.url = args.url or os.getenv('ODOO_URL', 'http://localhost:8069')
    args.db = args.db or os.getenv('ODOO_DB', 'aletheais')
    args.username = args.username or os.getenv('ODOO_USERNAME', 'admin@aletheais.com')
    args.password = args.password or os.getenv('ODOO_PASSWORD', 'orange5')

    return args


def test_module_install(module_name, url, db, username, password):
    """Test if a module can install without dependency errors."""
    try:
        ssl._create_default_https_context = ssl._create_unverified_context

        print('🧪 Testing module installation...')
        print(f'📦 Module: {module_name}')
        
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print('❌ Authentication failed')
            return False
            
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        # Check if module exists and is installable
        module_ids = models.execute_kw(db, uid, password, 'ir.module.module', 'search', [
            [('name', '=', module_name)]
        ])
        
        if not module_ids:
            print(f'❌ Module {module_name} not found')
            return False
            
        # Check current state
        modules = models.execute_kw(db, uid, password, 'ir.module.module', 'read', 
            [module_ids], {'fields': ['name', 'state']})
        
        current_state = modules[0]['state']
        print(f'📊 Current module state: {current_state}')
        
        if current_state == 'installed':
            print('✅ Module already installed and working')
            return True
        elif current_state == 'uninstalled':
            print('⏳ Attempting installation...')
            # Try to install
            result = models.execute_kw(db, uid, password, 'ir.module.module', 
                'button_immediate_install', [module_ids])
            print('✅ Installation successful!')
            return True
        else:
            print(f'⚠️  Module in {current_state} state')
            return True
            
    except Exception as e:
        error_str = str(e)
        if 'External ID not found' in error_str:
            print('❌ DEPENDENCY ERROR: Forward reference detected')
            print('💡 Fix: Reorder files in __manifest__.py')
        elif 'ParseError' in error_str:
            print('❌ XML PARSING ERROR: Invalid XML structure')
            print('💡 Fix: Check XML syntax and references')
        else:
            print(f'❌ Installation failed: {error_str[:200]}')
        
        print('\n🔧 Quick fixes to try:')
        print('1. Check .copilot-rules.md for proper manifest order')
        print('2. Ensure menu.xml loads AFTER all view files')
        print(f'3. Check manifest/data order for module: {module_name}')
        
        return False

if __name__ == '__main__':
    args = parse_args()
    success = test_module_install(
        module_name=args.module,
        url=args.url,
        db=args.db,
        username=args.username,
        password=args.password,
    )
    sys.exit(0 if success else 1)