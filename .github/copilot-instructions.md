# Copilot Instructions for Aletheais Odoo Project

## Project Overview
This is an **Odoo 18** ERP system running in Docker containers. The project uses:
- PostgreSQL 15 for data persistence
- Custom Odoo modules in `custom-addons/`
- Standard Odoo addons path: `/usr/lib/python3/dist-packages/odoo/addons`, `/mnt/odoo/addons`, `/mnt/odoo/custom-addons`

## Architecture & Structure

### Docker Services
- **db**: PostgreSQL 15 with health checks
- **odoo**: Odoo 18 in development mode (`--dev=reload,qweb,xml,assets,rpc`)
- **pgadmin**: Optional DB GUI on port 8081

### Key Directories
- `custom-addons/`: Custom Odoo modules (currently: `website_footer_override`)
- `addons/`: Additional third-party addons (mounted but currently empty)
- `config/`: Odoo configuration files
  - `odoo.conf`: Active config with DB connection, dev settings, addons paths
  - `odoo.conf.sample`: Template for reference

### Environment Configuration
All deployment settings are in `.env`:
- Database: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- Odoo version: `ODOO_VERSION=18`
- Ports: `HOST_HTTP_PORT=8069`, `HOST_LONGPOLL_PORT=8072`
- Admin password: `ODOO_ADMIN_PASSWD=orange5`

## Developer Workflows

### Starting the Application
```bash
docker-compose up -d
# Access Odoo at http://localhost:8069
# Access pgAdmin at http://localhost:8081
```

### Development Mode
Odoo runs with `--dev=reload,qweb,xml,assets,rpc` for live reloading:
- Python changes: Auto-reload
- XML/QWeb templates: Auto-reload
- Assets (CSS/JS): Auto-rebuild
- Single-process mode (`workers=0` in config) for easier debugging

### Module Development
1. Create module in `custom-addons/<module_name>/`
2. Required files:
   - `__manifest__.py` with `name`, `version`, `depends`, `data`, `installable`
   - `__init__.py` if adding Python models
3. After adding files, restart Odoo: `docker-compose restart odoo`
4. Install via Odoo UI: Apps → Update Apps List → Install

### Database Access
- Via pgAdmin: http://localhost:8081 (admin@aletheais.com / admin123)
- Direct: `docker exec -it <container> psql -U odoo -d postgres`

## Odoo Module Conventions

### Manifest Structure (v18)
See [`custom-addons/website_footer_override/__manifest__.py`](custom-addons/website_footer_override/__manifest__.py):
```python
{
    "name": "Module Name",
    "version": "18.0.1.0.0",  # Format: <odoo_version>.<major>.<minor>.<patch>
    "depends": ["base", "website"],
    "data": ["views/file.xml"],
    "installable": True,
}
```

### View Inheritance Pattern
This project uses **XPath inheritance** to override Odoo templates. See [`footer_override.xml`](custom-addons/website_footer_override/views/footer_override.xml):
```xml
<template id="custom_id" 
          inherit_id="module.original_template_id"
          name="Description">
    <xpath expr="//div[@class='target']" position="replace">
        <!-- Replacement content -->
    </xpath>
</template>
```

## Critical Configuration Details

### Addons Path Order
Defined in [`config/odoo.conf`](config/odoo.conf#L17):
```
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/odoo/addons,/mnt/odoo/custom-addons
```
Custom modules in `custom-addons/` override standard modules due to path precedence.

### Dev Settings in odoo.conf
- `limit_time_cpu = 0` and `limit_time_real = 0`: No request timeouts for debugging
- `workers = 0`: Single-process mode (required for `--dev` flag)

## Common Pitfalls
1. **Module not appearing**: Run "Update Apps List" in Odoo after adding new modules
2. **Changes not reflecting**: Ensure `--dev` flags are active; check container logs with `docker-compose logs odoo`
3. **Port conflicts**: Default ports 8069, 8072, 8081 must be available
4. **DB connection issues**: Wait for DB health check; check logs with `docker-compose logs db`

## Adding New Features
When creating new Odoo modules:
1. Follow the naming convention: `module_name` (lowercase, underscores)
2. Create proper `__manifest__.py` with all dependencies
3. Use view inheritance instead of replacing templates when possible
4. Test in dev mode before deploying
