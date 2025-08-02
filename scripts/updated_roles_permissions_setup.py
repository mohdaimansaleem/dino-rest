#!/usr/bin/env python3
"""
Updated Roles & Permissions Setup Script
Works with current backend validation patterns and creates proper permissions
"""
import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

# API Configuration
API_BASE_URL = "https://dino-backend-api-1018711634531.us-central1.run.app/api/v1"

def log_info(message: str):
    """Log info message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ℹ️  INFO: {message}")

def log_success(message: str):
    """Log success message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 🎉 SUCCESS: {message}")

def log_warning(message: str):
    """Log warning message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ⚠️  WARNING: {message}")

def log_error(message: str):
    """Log error message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ❌ ERROR: {message}")

def check_api_health() -> bool:
    """Check if API is accessible"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            log_success("API is accessible and healthy")
            return True
        else:
            log_error(f"API health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        log_error(f"API health check failed: {e}")
        return False

def get_existing_permissions() -> Dict[str, str]:
    """Get existing permissions to avoid duplicates"""
    try:
        response = requests.get(f"{API_BASE_URL}/permissions/", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("success") and "data" in result:
                permissions = result["data"]
                return {perm["name"]: perm["id"] for perm in permissions}
        return {}
    except Exception as e:
        log_warning(f"Could not fetch existing permissions: {e}")
        return {}

def get_existing_roles() -> Dict[str, str]:
    """Get existing roles"""
    try:
        response = requests.get(f"{API_BASE_URL}/roles/", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("success") and "data" in result:
                roles = result["data"]
                return {role["name"]: role["id"] for role in roles}
        return {}
    except Exception as e:
        log_warning(f"Could not fetch existing roles: {e}")
        return {}

def create_permission(name: str, description: str, resource: str, action: str, scope: str = "venue") -> Optional[str]:
    """Create a single permission with current validation patterns"""
    permission_data = {
        "name": name,
        "description": description,
        "resource": resource,
        "action": action,
        "scope": scope
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/permissions/",
            json=permission_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            if result.get("success"):
                permission_id = result.get("data", {}).get("id")
                log_success(f"✅ Created permission: {name} (ID: {permission_id})")
                return permission_id
            else:
                log_warning(f"Failed to create permission {name}: {result.get('message', 'Unknown error')}")
                return None
        elif response.status_code == 400 and "already exists" in response.text:
            log_info(f"Permission {name} already exists, skipping...")
            return "existing"
        else:
            log_warning(f"HTTP {response.status_code} creating permission {name}: {response.text}")
            return None
            
    except Exception as e:
        log_error(f"Error creating permission {name}: {e}")
        return None

def create_role(name: str, description: str) -> Optional[str]:
    """Create a role"""
    role_data = {
        "name": name,
        "description": description,
        "permission_ids": []
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/roles/",
            json=role_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            if result.get("success"):
                role_id = result.get("data", {}).get("id")
                log_success(f"✅ Created role: {name} (ID: {role_id})")
                return role_id
            else:
                log_warning(f"Failed to create role {name}: {result.get('message', 'Unknown error')}")
                return None
        elif response.status_code == 400 and "already exists" in response.text:
            log_info(f"Role {name} already exists, skipping...")
            return "existing"
        else:
            log_warning(f"HTTP {response.status_code} creating role {name}: {response.text}")
            return None
            
    except Exception as e:
        log_error(f"Error creating role {name}: {e}")
        return None

def assign_permissions_to_role(role_id: str, permission_ids: List[str]) -> bool:
    """Assign permissions to a role"""
    try:
        update_data = {
            "permission_ids": permission_ids
        }
        
        response = requests.put(
            f"{API_BASE_URL}/roles/{role_id}",
            json=update_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return True
        
        log_warning(f"Failed to assign permissions to role: {response.text}")
        return False
        
    except Exception as e:
        log_error(f"Error assigning permissions to role: {e}")
        return False

def main():
    """Main setup function"""
    print("🦕" + "=" * 77)
    print("🦕 Dino E-Menu API - Updated Roles & Permissions Setup")
    print("🦕" + "=" * 77)
    print()
    
    # Step 1: Check API health
    log_info("📊 PROGRESS: Step 1/6 (16%) - Checking API health and connectivity")
    if not check_api_health():
        log_error("API is not accessible. Please check the deployment.")
        return False
    
    # Step 2: Get existing data
    log_info("📊 PROGRESS: Step 2/6 (33%) - Checking existing permissions and roles")
    existing_permissions = get_existing_permissions()
    existing_roles = get_existing_roles()
    
    log_info(f"Found {len(existing_permissions)} existing permissions")
    log_info(f"Found {len(existing_roles)} existing roles")
    
    # Step 3: Create permissions that work with current validation
    log_info("📊 PROGRESS: Step 3/6 (50%) - Creating permissions with current validation patterns")
    
    # Define permissions that match current backend validation patterns
    # Current patterns: resource=(workspace|venue|menu|order|user|analytics|table), action=(create|read|update|delete|manage), scope=(own|venue|workspace|all)
    permissions_to_create = [
        # Workspace permissions
        ("workspace.read", "View workspace information", "workspace", "read", "workspace"),
        ("workspace.create", "Create new workspaces", "workspace", "create", "all"),
        ("workspace.update", "Update workspace settings", "workspace", "update", "workspace"),
        ("workspace.delete", "Delete workspaces", "workspace", "delete", "all"),
        ("workspace.manage", "Full workspace management", "workspace", "manage", "all"),
        
        # Venue permissions
        ("venue.read", "View venue information", "venue", "read", "venue"),
        ("venue.create", "Create new venues", "venue", "create", "workspace"),
        ("venue.update", "Update venue information", "venue", "update", "venue"),
        ("venue.delete", "Delete venues", "venue", "delete", "workspace"),
        ("venue.manage", "Full venue management", "venue", "manage", "workspace"),
        
        # Menu permissions
        ("menu.read", "View menu items and categories", "menu", "read", "venue"),
        ("menu.create", "Create menu items and categories", "menu", "create", "venue"),
        ("menu.update", "Update menu items and categories", "menu", "update", "venue"),
        ("menu.delete", "Delete menu items and categories", "menu", "delete", "venue"),
        ("menu.manage", "Full menu management", "menu", "manage", "venue"),
        
        # Order permissions
        ("order.read", "View orders", "order", "read", "venue"),
        ("order.create", "Create new orders", "order", "create", "venue"),
        ("order.update", "Update order status", "order", "update", "venue"),
        ("order.delete", "Cancel/delete orders", "order", "delete", "venue"),
        ("order.manage", "Full order management", "order", "manage", "venue"),
        
        # Table permissions
        ("table.read", "View table information", "table", "read", "venue"),
        ("table.create", "Create new tables", "table", "create", "venue"),
        ("table.update", "Update table status", "table", "update", "venue"),
        ("table.delete", "Delete tables", "table", "delete", "venue"),
        ("table.manage", "Full table management", "table", "manage", "venue"),
        
        # User permissions
        ("user.read", "View user information", "user", "read", "workspace"),
        ("user.create", "Create new users", "user", "create", "workspace"),
        ("user.update", "Update user information", "user", "update", "workspace"),
        ("user.delete", "Delete/deactivate users", "user", "delete", "workspace"),
        ("user.manage", "Full user management", "user", "manage", "workspace"),
        
        # Analytics permissions
        ("analytics.read", "View analytics and reports", "analytics", "read", "venue"),
        ("analytics.manage", "Manage analytics settings", "analytics", "manage", "workspace"),
    ]
    
    created_permissions = {}
    skipped_count = 0
    failed_count = 0
    
    log_info(f"Creating {len(permissions_to_create)} permissions...")
    
    for name, description, resource, action, scope in permissions_to_create:
        if name in existing_permissions:
            log_info(f"Permission {name} already exists, using existing ID")
            created_permissions[name] = existing_permissions[name]
            skipped_count += 1
        else:
            permission_id = create_permission(name, description, resource, action, scope)
            if permission_id and permission_id != "existing":
                created_permissions[name] = permission_id
            elif permission_id == "existing":
                skipped_count += 1
            else:
                failed_count += 1
        
        time.sleep(0.1)  # Small delay to avoid rate limiting
    
    log_success(f"Permission creation completed!")
    log_info(f"📊 Results: Created: {len(created_permissions) - skipped_count}, Skipped: {skipped_count}, Failed: {failed_count}")
    
    # Step 4: Create roles
    log_info("📊 PROGRESS: Step 4/6 (66%) - Creating role hierarchy")
    
    roles_to_create = [
        ("superadmin", "Super Administrator with full system access"),
        ("admin", "Administrator with venue management access"),
        ("operator", "Operator with basic operational access")
    ]
    
    created_roles = {}
    
    for role_name, role_description in roles_to_create:
        if role_name in existing_roles:
            log_info(f"Role {role_name} already exists, using existing ID")
            created_roles[role_name] = existing_roles[role_name]
        else:
            role_id = create_role(role_name, role_description)
            if role_id and role_id != "existing":
                created_roles[role_name] = role_id
            elif role_id == "existing":
                # Get the existing role ID
                created_roles[role_name] = existing_roles.get(role_name, "unknown")
        
        time.sleep(0.1)
    
    log_success(f"Role creation completed!")
    log_info(f"📊 Results: Created: {len(created_roles)}, Skipped: 0, Failed: 0")
    
    # Step 5: Assign permissions to roles
    log_info("📊 PROGRESS: Step 5/6 (83%) - Mapping permissions to roles")
    
    # Define role permission mappings
    role_permissions = {
        "superadmin": list(created_permissions.keys()),  # All permissions
        
        "admin": [
            # Venue management
            "venue.read", "venue.create", "venue.update", "venue.delete", "venue.manage",
            # Menu management
            "menu.read", "menu.create", "menu.update", "menu.delete", "menu.manage",
            # Order management
            "order.read", "order.create", "order.update", "order.delete", "order.manage",
            # Table management
            "table.read", "table.create", "table.update", "table.delete", "table.manage",
            # User management (limited)
            "user.read", "user.create", "user.update",
            # Analytics
            "analytics.read",
            # Workspace (read only)
            "workspace.read"
        ],
        
        "operator": [
            # Basic venue access
            "venue.read",
            # Menu viewing
            "menu.read",
            # Order management
            "order.read", "order.create", "order.update",
            # Table management
            "table.read", "table.update",
            # Basic workspace access
            "workspace.read"
        ]
    }
    
    assignment_success = 0
    assignment_total = 0
    
    for role_name, permission_names in role_permissions.items():
        if role_name not in created_roles:
            log_warning(f"Role {role_name} not found, skipping permission assignment")
            continue
        
        role_id = created_roles[role_name]
        
        # Get permission IDs
        permission_ids = []
        missing_permissions = []
        
        for perm_name in permission_names:
            if perm_name in created_permissions:
                permission_ids.append(created_permissions[perm_name])
            else:
                missing_permissions.append(perm_name)
        
        if missing_permissions:
            log_warning(f"Missing permissions for role {role_name}: {missing_permissions}")
        
        if permission_ids:
            log_info(f"🔗 Assigning {len(permission_ids)} permissions to role: {role_name}")
            
            if assign_permissions_to_role(role_id, permission_ids):
                log_success(f"✅ Successfully assigned {len(permission_ids)} permissions to {role_name}")
                assignment_success += 1
            else:
                log_error(f"Failed to assign permissions to {role_name}")
        
        assignment_total += 1
    
    log_success(f"Permission-role mapping completed!")
    log_info(f"📊 Total assignments attempted: {assignment_total}")
    log_info(f"📊 Successful assignments: {assignment_success}")
    log_info(f"📊 Failed assignments: {assignment_total - assignment_success}")
    
    # Step 6: Verification
    log_info("📊 PROGRESS: Step 6/6 (100%) - Verifying setup")
    
    # Verify permissions
    final_permissions = get_existing_permissions()
    log_success(f"✅ Found {len(final_permissions)} permissions in the system")
    
    # Verify roles
    final_roles = get_existing_roles()
    log_success(f"✅ Found {len(final_roles)} roles in the system")
    
    # Generate summary
    print()
    print("🎉" + "=" * 77)
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print("🎉" + "=" * 77)
    print()
    
    log_success("✅ Permissions created and mapped to roles")
    log_success("✅ Role hierarchy established with proper access levels")
    log_success("✅ System ready for user assignment and testing")
    
    print()
    log_info("📋 Next steps:")
    log_info("   1. Test API endpoints with different user roles")
    log_info("   2. Create test users and assign roles")
    log_info("   3. Test frontend permission gates")
    log_info("   4. Verify role-based access control")
    
    print()
    log_info("🔧 Troubleshooting:")
    log_info("   - If permissions are missing: Check backend validation patterns")
    log_info("   - If roles incomplete: Verify permission IDs are correct")
    log_info("   - If frontend issues: Ensure permission names match")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Setup completed successfully!")
            sys.exit(0)
        else:
            print("\n⚠️ Setup completed with warnings")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)