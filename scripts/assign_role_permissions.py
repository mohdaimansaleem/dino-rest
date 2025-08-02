#!/usr/bin/env python3
"""
Role Permission Assignment Script
Assigns the correct permissions to each role based on the hierarchy
"""
import requests
import json
import sys
from datetime import datetime

# API Configuration
API_BASE_URL = "https://dino-backend-api-1018711634531.us-central1.run.app/api/v1"

def get_all_permissions():
    """Get all available permissions"""
    try:
        response = requests.get(f"{API_BASE_URL}/permissions/", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                permissions = result.get("data", [])
                return {perm["name"]: perm["id"] for perm in permissions}
        return {}
    except Exception as e:
        print(f"❌ Error fetching permissions: {e}")
        return {}

def get_all_roles():
    """Get all available roles"""
    try:
        response = requests.get(f"{API_BASE_URL}/roles/", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                roles = result.get("data", [])
                return {role["name"]: role["id"] for role in roles}
        return {}
    except Exception as e:
        print(f"❌ Error fetching roles: {e}")
        return {}

def assign_permissions_to_role(role_id, permission_ids):
    """Assign permissions to a role"""
    try:
        # Get current role data
        response = requests.get(f"{API_BASE_URL}/roles/{role_id}", timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to get role data")
            return False
        
        role_data = response.json().get("data", {})
        
        # Update with new permissions
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
        
        print(f"❌ Failed to assign permissions: {response.text}")
        return False
        
    except Exception as e:
        print(f"❌ Error assigning permissions: {e}")
        return False

def main():
    """Assign permissions to roles based on hierarchy"""
    print("🔧 Assigning Permissions to Roles")
    print("=" * 50)
    
    # Get all permissions and roles
    permissions = get_all_permissions()
    roles = get_all_roles()
    
    if not permissions:
        print("❌ No permissions found. Run fix_permissions_setup.py first.")
        return False
    
    if not roles:
        print("❌ No roles found. Create roles first.")
        return False
    
    print(f"📊 Found {len(permissions)} permissions and {len(roles)} roles")
    print()
    
    # Define role permission mappings
    role_permissions = {
        "superadmin": list(permissions.keys()),  # All permissions
        
        "admin": [
            # Venue management
            "venue.read", "venue.create", "venue.update", "venue.activate", "venue.deactivate", "venue.switch",
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
            # Dashboard
            "dashboard.view", "dashboard.manage",
            # Settings
            "settings.view", "settings.update",
            # QR Codes
            "qr.generate", "qr.print", "qr.manage",
            # Reports
            "reports.view", "reports.create",
            # Notifications
            "notifications.manage",
            # Profile
            "profile.read", "profile.update",
            # Password
            "password.update"
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
            # Basic dashboard
            "dashboard.view",
            # Basic settings
            "settings.view",
            # QR generation
            "qr.generate",
            # Profile management
            "profile.read", "profile.update",
            # Password change
            "password.update"
        ]
    }
    
    # Assign permissions to each role
    success_count = 0
    total_assignments = 0
    
    for role_name, role_permission_names in role_permissions.items():
        if role_name not in roles:
            print(f"⚠️ Role '{role_name}' not found, skipping...")
            continue
        
        role_id = roles[role_name]
        
        # Get permission IDs for this role
        permission_ids = []
        missing_permissions = []
        
        for perm_name in role_permission_names:
            if perm_name in permissions:
                permission_ids.append(permissions[perm_name])
            else:
                missing_permissions.append(perm_name)
        
        if missing_permissions:
            print(f"⚠️ Missing permissions for role '{role_name}':")
            for perm in missing_permissions:
                print(f"   - {perm}")
        
        if permission_ids:
            print(f"🔗 Assigning {len(permission_ids)} permissions to role '{role_name}'...")
            
            if assign_permissions_to_role(role_id, permission_ids):
                print(f"✅ Successfully assigned permissions to '{role_name}'")
                success_count += 1
            else:
                print(f"❌ Failed to assign permissions to '{role_name}'")
        
        total_assignments += 1
        print()
    
    print("=" * 50)
    print(f"✅ Successfully assigned permissions to {success_count}/{total_assignments} roles")
    
    # Generate summary report
    print()
    print("📊 Permission Assignment Summary:")
    print()
    
    for role_name in role_permissions.keys():
        if role_name in roles:
            assigned_count = len([p for p in role_permissions[role_name] if p in permissions])
            total_count = len(role_permissions[role_name])
            print(f"{role_name.title()}: {assigned_count}/{total_count} permissions assigned")
    
    print()
    print("🚀 Next Steps:")
    print("1. Test role-based access with different user accounts")
    print("2. Verify frontend permission gates work correctly")
    print("3. Create test users and assign appropriate roles")
    print("4. Test API endpoints with different role permissions")
    
    return success_count == total_assignments

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 All role permissions assigned successfully!")
            sys.exit(0)
        else:
            print("\n⚠️ Some role assignments failed")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Assignment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Assignment failed with error: {e}")
        sys.exit(1)