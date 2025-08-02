# Dino E-Menu - Roles & Permissions Setup

## Overview

This directory contains the improved roles and permissions setup script for the Dino E-Menu API.

## Scripts

### `setup_roles_permissions.sh` ✨ **WORKING & TESTED**

Modern, maintainable script that replaces the old complex version.

**Features:**
- ✅ Clean, readable code with proper bash standards
- ✅ Easy to extend and modify
- ✅ Robust error handling and logging
- ✅ Idempotent operations (safe to re-run)
- ✅ Dry-run mode for testing
- ✅ Proper JSON formatting (no more escaping issues)
- ✅ Configuration-driven approach

**Usage:**
```bash
# Basic setup
./scripts/setup_roles_permissions.sh

# Verbose output
./scripts/setup_roles_permissions.sh --verbose

# Test without making changes
./scripts/setup_roles_permissions.sh --dry-run

# Custom API URL
./scripts/setup_roles_permissions.sh --url https://your-api.com

# Help
./scripts/setup_roles_permissions.sh --help
```

## What It Creates

### Permissions (38 total)
- **Workspace**: view, create, update, delete, manage
- **Venue**: view, create, read, update, delete, manage
- **Menu**: view, create, read, update, delete, manage
- **Order**: view, create, read, update, delete, manage
- **Table**: view, create, read, update, delete, manage
- **User**: view, create, read, update, delete, manage
- **Analytics**: view, read, manage

### Roles (3 total)
- **SuperAdmin**: All permissions (38)
- **Admin**: Full management permissions (38)
- **Operator**: Limited operational permissions (16)

## Adding New Permissions

1. **Add to permission list** in `get_all_permissions()`:
   ```bash
   echo "existing permissions new_resource.new_action"
   ```

2. **Add configuration** in `get_permission_config()`:
   ```bash
   "new_resource.new_action") echo "Description|resource|action|scope" ;;
   ```

3. **Update role permissions** in `get_role_permissions()`:
   ```bash
   "admin") echo "existing permissions new_resource.new_action" ;;
   ```

## Adding New Roles

1. **Add to role list** in `get_all_roles()`:
   ```bash
   echo "superadmin admin operator new_role"
   ```

2. **Add configuration** in `get_role_config()`:
   ```bash
   "new_role") echo "Display Name|Description" ;;
   ```

3. **Add permissions** in `get_role_permissions()`:
   ```bash
   "new_role") echo "permission1 permission2 permission3" ;;
   ```

## Key Improvements Over Old Script

| Aspect | Old Script | New Script |
|--------|------------|------------|
| **Lines of Code** | 1000+ | ~600 |
| **Complexity** | High | Low |
| **Maintainability** | Poor | Excellent |
| **Error Handling** | Complex | Simple & Robust |
| **JSON Issues** | Frequent | None |
| **Extensibility** | Difficult | Easy |
| **Testing** | No dry-run | Full dry-run support |
| **Standards** | Mixed | Modern bash best practices |

## Environment Variables

- `API_BASE_URL`: API base URL (default: production URL)
- `VERBOSE`: Set to 'true' for detailed output
- `DRY_RUN`: Set to 'true' for dry-run mode

## Prerequisites

- Bash 4.0+
- curl
- gcloud CLI (for authentication)
- jq (optional, for better JSON parsing)

## Troubleshooting

### Common Issues

1. **Permission denied**: Make sure script is executable
   ```bash
   chmod +x scripts/setup_roles_permissions.sh
   ```

2. **Authentication errors**: Ensure gcloud is configured
   ```bash
   gcloud auth login
   ```

3. **API not accessible**: Check the API URL and network connectivity

### Debug Mode

Run with verbose flag to see detailed output:
```bash
./scripts/setup_roles_permissions.sh --verbose
```

## Migration from Old Script

The new script is a complete replacement. Simply use `setup_roles_permissions.sh` instead of `complete_roles_permissions_setup.sh`.

**Benefits of migration:**
- ✅ No more JSON formatting errors
- ✅ Faster execution
- ✅ Better error messages
- ✅ Easier to maintain and extend
- ✅ Modern bash practices
- ✅ Comprehensive testing support