#!/usr/bin/env python3
"""
Check Current Backend Validation Patterns
Tests what validation patterns are currently active in the deployed API
"""
import requests
import json
from datetime import datetime

API_BASE_URL = "https://dino-backend-api-1018711634531.us-central1.run.app/api/v1"

def log_info(message: str):
    """Log info message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ℹ️  {message}")

def log_success(message: str):
    """Log success message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ✅ {message}")

def log_error(message: str):
    """Log error message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ❌ {message}")

def test_permission_creation(name, resource, action, scope):
    """Test creating a permission to see validation response"""
    permission_data = {
        "name": name,
        "description": f"Test permission for {name}",
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
                return "SUCCESS", result.get("data", {}).get("id", "unknown")
            else:
                return "FAILED", result.get("message", "Unknown error")
        else:
            try:
                error_detail = response.json()
                return "VALIDATION_ERROR", error_detail
            except:
                return "HTTP_ERROR", f"HTTP {response.status_code}: {response.text}"
                
    except Exception as e:
        return "EXCEPTION", str(e)

def main():
    """Test current validation patterns"""
    print("🔍" + "=" * 70)
    print("🔍 Checking Current Backend Validation Patterns")
    print("🔍" + "=" * 70)
    print()
    
    # Test 1: Check API health
    log_info("Testing API connectivity...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            log_success("API is accessible")
        else:
            log_error(f"API health check failed: HTTP {response.status_code}")
            return
    except Exception as e:
        log_error(f"API not accessible: {e}")
        return
    
    # Test 2: Check existing permissions to understand current patterns
    log_info("Fetching existing permissions to understand current patterns...")
    try:
        response = requests.get(f"{API_BASE_URL}/permissions/", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("success") and "data" in result:
                permissions = result["data"]
                log_success(f"Found {len(permissions)} existing permissions")
                
                # Analyze patterns
                resources = set()
                actions = set()
                scopes = set()
                
                for perm in permissions[:10]:  # Analyze first 10
                    resources.add(perm.get("resource", "unknown"))
                    actions.add(perm.get("action", "unknown"))
                    scopes.add(perm.get("scope", "unknown"))
                
                print()
                log_info("Current patterns found in existing permissions:")
                print(f"   Resources: {sorted(resources)}")
                print(f"   Actions: {sorted(actions)}")
                print(f"   Scopes: {sorted(scopes)}")
                print()
            else:
                log_error("Could not fetch permissions data")
        else:
            log_error(f"Failed to fetch permissions: HTTP {response.status_code}")
    except Exception as e:
        log_error(f"Error fetching permissions: {e}")
    
    # Test 3: Test various validation patterns
    log_info("Testing validation patterns...")
    print()
    
    test_cases = [
        # Test current known working patterns
        ("workspace.read", "workspace", "read", "workspace"),
        ("venue.create", "venue", "create", "venue"),
        ("menu.update", "menu", "update", "venue"),
        ("order.delete", "order", "delete", "venue"),
        ("table.manage", "table", "manage", "venue"),
        ("user.read", "user", "read", "workspace"),
        ("analytics.read", "analytics", "read", "venue"),
        
        # Test patterns that might fail
        ("dashboard.view", "dashboard", "view", "venue"),
        ("settings.view", "settings", "view", "venue"),
        ("qr.generate", "qr", "generate", "venue"),
        ("reports.view", "reports", "view", "venue"),
        ("notifications.manage", "notifications", "manage", "venue"),
        ("profile.update", "profile", "update", "own"),
        
        # Test with different scopes
        ("workspace.create", "workspace", "create", "system"),
        ("venue.switch", "venue", "switch", "workspace"),
        ("menu.view", "menu", "view", "venue"),
    ]
    
    working_patterns = []
    failing_patterns = []
    
    for name, resource, action, scope in test_cases:
        status, result = test_permission_creation(name, resource, action, scope)
        
        if status == "SUCCESS":
            log_success(f"✅ WORKS: {name} ({resource}.{action}, scope: {scope})")
            working_patterns.append((resource, action, scope))
            # Clean up test permission
            try:
                requests.delete(f"{API_BASE_URL}/permissions/{result}", timeout=5)
            except:
                pass
        elif status == "VALIDATION_ERROR":
            log_error(f"❌ FAILS: {name} - Validation error")
            failing_patterns.append((name, resource, action, scope, result))
        else:
            log_error(f"❌ ERROR: {name} - {result}")
    
    # Summary
    print()
    print("📊" + "=" * 70)
    print("📊 VALIDATION PATTERN ANALYSIS")
    print("📊" + "=" * 70)
    print()
    
    if working_patterns:
        log_success(f"Working patterns ({len(working_patterns)}):")
        working_resources = set(p[0] for p in working_patterns)
        working_actions = set(p[1] for p in working_patterns)
        working_scopes = set(p[2] for p in working_patterns)
        
        print(f"   ✅ Resources: {sorted(working_resources)}")
        print(f"   ✅ Actions: {sorted(working_actions)}")
        print(f"   ✅ Scopes: {sorted(working_scopes)}")
        print()
    
    if failing_patterns:
        log_error(f"Failing patterns ({len(failing_patterns)}):")
        for name, resource, action, scope, error in failing_patterns[:5]:  # Show first 5
            print(f"   ❌ {name}: {resource}.{action} (scope: {scope})")
            if isinstance(error, dict) and "detail" in error:
                for detail in error["detail"][:2]:  # Show first 2 error details
                    print(f"      - {detail.get('msg', 'Unknown error')}")
        print()
    
    # Recommendations
    print("💡" + "=" * 70)
    print("💡 RECOMMENDATIONS")
    print("💡" + "=" * 70)
    print()
    
    if working_patterns:
        log_info("Use these patterns for creating permissions:")
        working_resources = sorted(set(p[0] for p in working_patterns))
        working_actions = sorted(set(p[1] for p in working_patterns))
        working_scopes = sorted(set(p[2] for p in working_patterns))
        
        print(f"   Resources: {working_resources}")
        print(f"   Actions: {working_actions}")
        print(f"   Scopes: {working_scopes}")
        print()
        
        log_info("Example working permission:")
        if working_patterns:
            example = working_patterns[0]
            print(f"   {{")
            print(f"     \"name\": \"{example[0]}.{example[1]}\",")
            print(f"     \"resource\": \"{example[0]}\",")
            print(f"     \"action\": \"{example[1]}\",")
            print(f"     \"scope\": \"{example[2]}\",")
            print(f"     \"description\": \"Description here\"")
            print(f"   }}")
    
    print()
    log_info("Next steps:")
    print("   1. Use the updated_roles_permissions_setup.py script")
    print("   2. Only create permissions with working patterns")
    print("   3. Map frontend requirements to working backend patterns")
    print("   4. Update frontend to use backend-compatible permission names")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Check interrupted by user")
    except Exception as e:
        print(f"\n❌ Check failed with error: {e}")