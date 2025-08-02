#!/usr/bin/env python3
"""
Fixed Permissions Setup Script
Creates permissions that match the frontend requirements with proper validation
"""
import requests
import json
import sys
from datetime import datetime

# API Configuration
API_BASE_URL = "https://dino-backend-api-1018711634531.us-central1.run.app/api/v1"

def create_permission(name, description, resource, action, scope="venue"):
    """Create a single permission with proper validation"""
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
                print(f"✅ Created permission: {name} (ID: {permission_id})")
                return permission_id
            else:
                print(f"❌ Failed to create permission {name}: {result.get('message', 'Unknown error')}")
                return None
        else:
            print(f"❌ HTTP {response.status_code} creating permission {name}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating permission {name}: {e}")
        return None

def main():
    """Create all required permissions with proper validation"""
    print("🔧 Creating Fixed Permissions for Dino E-Menu API")
    print("=" * 60)
    
    # Core permissions that match the schema validation
    permissions = [
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
        ("venue.activate", "Activate venues", "venue", "activate", "workspace"),
        ("venue.deactivate", "Deactivate venues", "venue", "deactivate", "workspace"),
        ("venue.switch", "Switch between venues", "venue", "switch", "workspace"),
        
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
        
        # Dashboard permissions
        ("dashboard.view", "Access dashboard", "dashboard", "view", "venue"),
        ("dashboard.manage", "Manage dashboard settings", "dashboard", "manage", "workspace"),
        
        # Settings permissions
        ("settings.view", "View settings", "settings", "view", "venue"),
        ("settings.update", "Update settings", "settings", "update", "venue"),
        ("settings.manage", "Full settings management", "settings", "manage", "workspace"),
        
        # QR Code permissions
        ("qr.generate", "Generate QR codes", "qr", "generate", "venue"),
        ("qr.print", "Print QR codes", "qr", "print", "venue"),
        ("qr.manage", "Manage QR code system", "qr", "manage", "venue"),
        
        # Reports permissions
        ("reports.view", "View reports", "reports", "view", "venue"),
        ("reports.create", "Create custom reports", "reports", "create", "venue"),
        ("reports.manage", "Manage reporting system", "reports", "manage", "workspace"),
        
        # Notifications permissions
        ("notifications.read", "View notifications", "notifications", "read", "own"),
        ("notifications.manage", "Manage notification settings", "notifications", "manage", "venue"),
        
        # Profile permissions
        ("profile.read", "View own profile", "profile", "read", "own"),
        ("profile.update", "Update own profile", "profile", "update", "own"),
        
        # Password permissions
        ("password.update", "Change password", "password", "update", "own"),
    ]
    
    created_permissions = {}
    failed_count = 0
    
    print(f"Creating {len(permissions)} permissions...")
    print()
    
    for name, description, resource, action, scope in permissions:
        permission_id = create_permission(name, description, resource, action, scope)
        if permission_id:
            created_permissions[name] = permission_id
        else:
            failed_count += 1
    
    print()
    print("=" * 60)
    print(f"✅ Successfully created: {len(created_permissions)} permissions")
    print(f"❌ Failed to create: {failed_count} permissions")
    print()
    
    # Save permission mapping for role assignment
    if created_permissions:
        mapping_file = f"permission_mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(mapping_file, 'w') as f:
            json.dump(created_permissions, f, indent=2)
        print(f"📄 Permission mapping saved to: {mapping_file}")
    
    # Display role recommendations
    print()
    print("🎯 Recommended Role Assignments:")
    print()
    print("SuperAdmin (All permissions):")
    for name in created_permissions.keys():
        print(f"  - {name}")
    
    print()
    print("Admin (Venue management permissions):")
    admin_permissions = [name for name in created_permissions.keys() 
                        if not name.startswith(('workspace.create', 'workspace.delete', 'user.manage'))]
    for name in admin_permissions:
        print(f"  - {name}")
    
    print()
    print("Operator (Basic operational permissions):")
    operator_permissions = [name for name in created_permissions.keys() 
                           if name.startswith(('order.', 'table.', 'menu.read', 'dashboard.view', 'profile.', 'password.'))]
    for name in operator_permissions:
        print(f"  - {name}")
    
    print()
    print("🚀 Next Steps:")
    print("1. Update role assignments using the permission IDs")
    print("2. Test the permissions with different user roles")
    print("3. Verify frontend permission gates work correctly")
    
    return len(created_permissions), failed_count

if __name__ == "__main__":
    try:
        created, failed = main()
        if failed > 0:
            sys.exit(1)
        else:
            print("\n🎉 All permissions created successfully!")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)