#!/usr/bin/env python3
"""
Menu Hierarchy Validator for Odoo

Checks for parent_path corruption that breaks menu visibility.
This is a common Odoo bug with NO built-in detection!

Usage:
    python3 scripts/validate_menu_hierarchy.py database_name
    python3 scripts/validate_menu_hierarchy.py database_name --host db --port 5432 --user odoo --password odoo
    python3 scripts/validate_menu_hierarchy.py database_name --host localhost --port 5433
    python3 scripts/validate_menu_hierarchy.py database_name --odoo-config ./config/odoo.conf
    
Or run inside Odoo container:
    docker compose exec odoo python3 /mnt/extra-addons/scripts/validate_menu_hierarchy.py npo
"""

import sys
import os
import argparse
import configparser


def parse_args():
    """Parse CLI arguments for menu hierarchy validation."""
    parser = argparse.ArgumentParser(
        description='Validate Odoo menu parent_path hierarchy in PostgreSQL.'
    )
    parser.add_argument(
        'database',
        help='Database name to validate'
    )
    parser.add_argument(
        '--odoo-config',
        default=None,
        help='Path to odoo.conf (defaults to ./config/odoo.conf or ../config/odoo.conf)'
    )
    parser.add_argument('--host', default=None, help='PostgreSQL host (or ODOO_DB_HOST)')
    parser.add_argument('--port', default=None, help='PostgreSQL port (or ODOO_DB_PORT)')
    parser.add_argument('--user', default=None, help='PostgreSQL user (or ODOO_DB_USER)')
    parser.add_argument('--password', default=None, help='PostgreSQL password (or ODOO_DB_PASSWORD)')

    args = parser.parse_args()
    conf_options = load_odoo_options(args.odoo_config)

    host_env = os.getenv('ODOO_DB_HOST')
    port_env = os.getenv('ODOO_DB_PORT')
    conf_host = conf_options.get('db_host')
    conf_port = conf_options.get('db_port')

    host_from_cli = args.host is not None
    port_from_cli = args.port is not None

    # Precedence: CLI arg > environment variable > odoo.conf > built-in default
    resolved_host = args.host or host_env or conf_host or 'db'
    port_value = args.port or port_env or conf_port or '5432'
    resolved_port = int(port_value)

    # Host-friendly fallback: if config points to Docker-internal db:5432 and
    # no CLI/ENV overrides are set, use localhost:5433 (published DB port).
    if (
        not host_from_cli
        and not host_env
        and conf_host == 'db'
        and not port_from_cli
        and not port_env
        and (conf_port is None or str(conf_port) == '5432')
    ):
        resolved_host = 'localhost'
        resolved_port = 5433

    args.host = resolved_host
    args.port = resolved_port
    args.user = args.user or os.getenv('ODOO_DB_USER') or conf_options.get('db_user') or 'odoo'
    args.password = (
        args.password
        or os.getenv('ODOO_DB_PASSWORD')
        or conf_options.get('db_password')
        or 'odoo'
    )

    return args


def load_odoo_options(config_path=None):
    """Load [options] from an Odoo config file if available."""
    if config_path:
        candidates = [config_path]
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(os.getcwd(), 'config', 'odoo.conf'),
            os.path.join(script_dir, '..', 'config', 'odoo.conf'),
        ]

    parser = configparser.ConfigParser()
    for candidate in candidates:
        if os.path.exists(candidate):
            parser.read(candidate)
            return dict(parser['options']) if parser.has_section('options') else {}

    return {}


def validate_menu_hierarchy(db_name, host='db', port=5432, user='odoo', password='odoo'):
    """
    Validate that all menu parent_path values are correct.
    
    Returns:
        dict: {
            'valid': bool,
            'errors': list of error dicts,
            'total_menus': int,
            'corrupted_menus': int
        }
    """
    try:
        import psycopg2
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency: install psycopg2 to run this script."
        ) from exc

    try:
        from tabulate import tabulate
    except ImportError:
        tabulate = None

    conn = psycopg2.connect(
        dbname=db_name,
        user=user,
        password=password,
        host=host,
        port=port,
    )
    cur = conn.cursor()
    
    # Get all menus with their parent relationships
    cur.execute("""
        SELECT 
            id,
            name->>'en_US' as name,
            parent_id,
            parent_path,
            active
        FROM ir_ui_menu
        ORDER BY id
    """)
    
    menus = cur.fetchall()
    errors = []
    fixes = []
    
    print(f"\n{'='*80}")
    print(f"🔍 Validating Menu Hierarchy for database: {db_name}")
    print(f"{'='*80}\n")
    
    for menu_id, name, parent_id, parent_path, active in menus:
        # Calculate expected parent_path
        if parent_id is None:
            expected_path = f"{menu_id}/"
        else:
            # Get parent's path
            cur.execute(
                "SELECT parent_path FROM ir_ui_menu WHERE id = %s",
                (parent_id,)
            )
            parent_result = cur.fetchone()
            
            if not parent_result:
                errors.append({
                    'menu_id': menu_id,
                    'name': name,
                    'error': f"Parent menu {parent_id} does not exist!",
                    'current_path': parent_path,
                    'expected_path': 'N/A',
                    'active': active
                })
                continue
            
            parent_path_value = parent_result[0]
            expected_path = f"{parent_path_value}{menu_id}/"
        
        # Compare actual vs expected
        if parent_path != expected_path:
            errors.append({
                'menu_id': menu_id,
                'name': name,
                'error': 'Corrupted parent_path',
                'current_path': parent_path or 'NULL',
                'expected_path': expected_path,
                'parent_id': parent_id,
                'active': active
            })
            
            fixes.append((menu_id, expected_path))
    
    cur.close()
    conn.close()
    
    # Print results
    total_menus = len(menus)
    corrupted = len(errors)
    
    if corrupted == 0:
        print(f"✅ All {total_menus} menus are valid!")
        print(f"   No parent_path corruption detected.\n")
        return {
            'valid': True,
            'errors': [],
            'total_menus': total_menus,
            'corrupted_menus': 0
        }
    else:
        print(f"❌ Found {corrupted} corrupted menus out of {total_menus} total!\n")
        
        # Print table of errors
        table_data = []
        for err in errors:
            table_data.append([
                err['menu_id'],
                err['name'][:30],
                'Y' if err['active'] else 'N',
                err.get('parent_id', 'N/A'),
                err['current_path'][:20],
                err['expected_path'][:20]
            ])
        
        if tabulate:
            print(tabulate(
                table_data,
                headers=['ID', 'Menu Name', 'Active', 'Parent', 'Current Path', 'Expected Path'],
                tablefmt='grid'
            ))
        else:
            print('tabulate not installed; using plain text output:\n')
            print('ID | Menu Name | Active | Parent | Current Path | Expected Path')
            print('-' * 80)
            for row in table_data:
                print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")
        
        # Generate fix SQL
        print(f"\n{'='*80}")
        print("🔧 SQL FIX COMMANDS:")
        print(f"{'='*80}\n")
        
        for menu_id, expected_path in fixes:
            print(f"UPDATE ir_ui_menu SET parent_path = '{expected_path}' WHERE id = {menu_id};")
        
        print(f"\n{'='*80}")
        print("💡 TIP: Run these commands, then restart Odoo:")
        print(f"{'='*80}")
        print(f"docker compose exec db psql -U {user} -d {db_name} << 'SQL'")
        for menu_id, expected_path in fixes:
            print(f"UPDATE ir_ui_menu SET parent_path = '{expected_path}' WHERE id = {menu_id};")
        print("SQL")
        print("\ndocker compose restart odoo")
        print()
        
        return {
            'valid': False,
            'errors': errors,
            'total_menus': total_menus,
            'corrupted_menus': corrupted,
            'fixes': fixes
        }


if __name__ == '__main__':
    args = parse_args()

    try:
        result = validate_menu_hierarchy(
            db_name=args.database,
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password,
        )
        sys.exit(0 if result['valid'] else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        sys.exit(2)
