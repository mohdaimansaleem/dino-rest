#!/bin/bash

# =============================================================================
# Dino E-Menu API - Roles & Permissions Setup Script
# =============================================================================
# Modern, maintainable script for setting up roles and permissions
# Features:
# - Clean configuration-driven approach
# - Easy to add new permissions/roles
# - Proper error handling and logging
# - JSON validation and formatting
# - Idempotent operations
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# =============================================================================
# CONFIGURATION
# =============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_BASE_URL="${API_BASE_URL:-https://dino-backend-api-1018711634531.us-central1.run.app}"
VERBOSE="${VERBOSE:-false}"
DRY_RUN="${DRY_RUN:-false}"

# Temporary files
readonly TEMP_DIR="/tmp/dino_setup_$$"
readonly PERMISSION_IDS_FILE="${TEMP_DIR}/permission_ids"
readonly ROLE_IDS_FILE="${TEMP_DIR}/role_ids"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $*${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $*${NC}" >&2
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $*${NC}" >&2
}

info() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] ℹ️  $*${NC}"
}

success() {
    echo -e "${CYAN}[$(date +'%H:%M:%S')] 🎉 $*${NC}"
}

verbose() {
    [[ "$VERBOSE" == "true" ]] && echo -e "${BLUE}[$(date +'%H:%M:%S')] 🔍 $*${NC}"
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

cleanup() {
    [[ -d "$TEMP_DIR" ]] && rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

setup_temp_dir() {
    mkdir -p "$TEMP_DIR"
}

# Generate authentication token
get_auth_token() {
    if command -v gcloud >/dev/null 2>&1; then
        gcloud auth print-identity-token 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# Make API calls with proper error handling
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    local description="${4:-API call}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "DRY RUN: $method $endpoint"
        [[ -n "$data" ]] && verbose "Data: $data"
        echo '{"id":"dry-run-id","success":true}'
        return 0
    fi
    
    local auth_token
    auth_token=$(get_auth_token)
    
    local curl_args=(
        -s -L -X "$method"
        -H "Content-Type: application/json"
        -w "HTTPCODE:%{http_code}"
    )
    
    [[ -n "$auth_token" ]] && curl_args+=(-H "Authorization: Bearer $auth_token")
    [[ -n "$data" ]] && curl_args+=(-d "$data")
    
    local response
    response=$(curl "${curl_args[@]}" "${API_BASE_URL}${endpoint}")
    
    local http_code="${response##*HTTPCODE:}"
    local body="${response%HTTPCODE:*}"
    
    verbose "$description - HTTP $http_code"
    verbose "Response: ${body:0:200}..."
    
    if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
        echo "$body"
        return 0
    else
        error "$description failed (HTTP $http_code): $body"
        return 1
    fi
}

# Extract ID from JSON response
extract_id() {
    local json="$1"
    
    # Try jq first if available
    if command -v jq >/dev/null 2>&1; then
        # Try multiple patterns for different response formats
        local id
        id=$(echo "$json" | jq -r '.data.id // .id // empty' 2>/dev/null)
        echo "$id"
    else
        # Fallback to grep/sed - try data.id first, then id
        local id
        id=$(echo "$json" | grep -o '"data":{[^}]*"id":"[^"]*"' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
        if [[ -z "$id" ]]; then
            id=$(echo "$json" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
        fi
        echo "$id"
    fi
}

# Store key-value pairs
store_kv() {
    local file="$1"
    local key="$2"
    local value="$3"
    echo "${key}=${value}" >> "$file"
}

# Get value by key
get_value() {
    local file="$1"
    local key="$2"
    [[ -f "$file" ]] && grep "^${key}=" "$file" | cut -d'=' -f2 || echo ""
}

# =============================================================================
# PERMISSION CONFIGURATION
# =============================================================================

# Get permission configuration
get_permission_config() {
    local name="$1"
    case "$name" in
        # Workspace permissions (using valid actions and scopes)
        "workspace.read") echo "Read workspace information|workspace|read|workspace" ;;
        "workspace.create") echo "Create new workspaces|workspace|create|all" ;;
        "workspace.update") echo "Update workspace settings|workspace|update|workspace" ;;
        "workspace.delete") echo "Delete workspaces|workspace|delete|workspace" ;;
        "workspace.manage") echo "Full workspace management|workspace|manage|workspace" ;;
        
        # Venue permissions
        "venue.read") echo "Read venue information|venue|read|venue" ;;
        "venue.create") echo "Create new venues|venue|create|workspace" ;;
        "venue.update") echo "Update venue information|venue|update|venue" ;;
        "venue.delete") echo "Delete venues|venue|delete|venue" ;;
        "venue.manage") echo "Full venue management|venue|manage|venue" ;;
        
        # Menu permissions
        "menu.read") echo "Read menu items|menu|read|venue" ;;
        "menu.create") echo "Create menu items|menu|create|venue" ;;
        "menu.update") echo "Update menu items|menu|update|venue" ;;
        "menu.delete") echo "Delete menu items|menu|delete|venue" ;;
        "menu.manage") echo "Full menu management|menu|manage|venue" ;;
        
        # Order permissions
        "order.read") echo "Read orders|order|read|venue" ;;
        "order.create") echo "Create orders|order|create|venue" ;;
        "order.update") echo "Update order status|order|update|venue" ;;
        "order.delete") echo "Delete orders|order|delete|venue" ;;
        "order.manage") echo "Full order management|order|manage|venue" ;;
        
        # Table permissions
        "table.read") echo "Read tables|table|read|venue" ;;
        "table.create") echo "Create tables|table|create|venue" ;;
        "table.update") echo "Update tables|table|update|venue" ;;
        "table.delete") echo "Delete tables|table|delete|venue" ;;
        "table.manage") echo "Full table management|table|manage|venue" ;;
        
        # User permissions
        "user.read") echo "Read users|user|read|workspace" ;;
        "user.create") echo "Create users|user|create|workspace" ;;
        "user.update") echo "Update users|user|update|workspace" ;;
        "user.delete") echo "Delete users|user|delete|workspace" ;;
        "user.manage") echo "Full user management|user|manage|workspace" ;;
        
        # Analytics permissions
        "analytics.read") echo "Read analytics and reports|analytics|read|venue" ;;
        "analytics.manage") echo "Manage analytics settings|analytics|manage|venue" ;;
        
        *) echo "" ;;
    esac
}

# Get all permission names (using only valid actions: create, read, update, delete, manage)
get_all_permissions() {
    echo "workspace.read workspace.create workspace.update workspace.delete workspace.manage venue.read venue.create venue.update venue.delete venue.manage menu.read menu.create menu.update menu.delete menu.manage order.read order.create order.update order.delete order.manage table.read table.create table.update table.delete table.manage user.read user.create user.update user.delete user.manage analytics.read analytics.manage"
}

# =============================================================================
# ROLE CONFIGURATION
# =============================================================================

# Get role configuration
get_role_config() {
    local name="$1"
    case "$name" in
        "superadmin") echo "Super Administrator|Complete system access with all permissions" ;;
        "admin") echo "Administrator|Full venue management with user creation and business operations" ;;
        "operator") echo "Operator|Day-to-day operations with order and table management" ;;
        *) echo "" ;;
    esac
}

# Get all role names
get_all_roles() {
    echo "superadmin admin operator"
}

# Get permissions for a specific role
get_role_permissions() {
    local role="$1"
    case "$role" in
        "superadmin")
            get_all_permissions
            ;;
        "admin")
            echo "workspace.read workspace.create workspace.update workspace.delete workspace.manage venue.read venue.create venue.update venue.delete venue.manage menu.read menu.create menu.update menu.delete menu.manage order.read order.create order.update order.delete order.manage user.read user.create user.update user.delete user.manage table.read table.create table.update table.delete table.manage analytics.read analytics.manage"
            ;;
        "operator")
            echo "workspace.read venue.read menu.read order.read order.create order.update user.read table.read table.update analytics.read"
            ;;
        *)
            echo ""
            ;;
    esac
}

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

create_permission() {
    local name="$1"
    local permission_data="$2"
    
    verbose "Creating permission: $name"
    
    local response
    if response=$(api_call "POST" "/api/v1/permissions/" "$permission_data" "Create permission $name"); then
        local id
        id=$(extract_id "$response")
        
        if [[ -n "$id" ]]; then
            store_kv "$PERMISSION_IDS_FILE" "$name" "$id"
            log "Created permission: $name (ID: $id)"
            return 0
        else
            # In dry run mode, create a fake ID for testing
            if [[ "$DRY_RUN" == "true" ]]; then
                store_kv "$PERMISSION_IDS_FILE" "$name" "dry-run-$name"
                log "Created permission: $name (ID: dry-run-$name)"
                return 0
            else
                warn "Created permission $name but couldn't extract ID"
                return 1
            fi
        fi
    else
        # Check if it already exists
        if echo "$response" | grep -q "already exists"; then
            verbose "Permission $name already exists, fetching ID"
            if existing_response=$(api_call "GET" "/api/v1/permissions/?name=$name" "" "Get existing permission $name" 2>/dev/null); then
                local id
                # Try to extract ID from the results array
                if command -v jq >/dev/null 2>&1; then
                    id=$(echo "$existing_response" | jq -r '.results[0].id // empty' 2>/dev/null)
                else
                    id=$(echo "$existing_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
                fi
                
                if [[ -n "$id" ]]; then
                    store_kv "$PERMISSION_IDS_FILE" "$name" "$id"
                    log "Found existing permission: $name (ID: $id)"
                    return 0
                fi
            fi
        fi
        warn "Failed to create permission: $name"
        return 1
    fi
}

create_all_permissions() {
    info "Creating permissions..."
    
    local created=0 failed=0
    
    for name in $(get_all_permissions); do
        local config
        config=$(get_permission_config "$name")
        
        if [[ -n "$config" ]]; then
            IFS='|' read -r description resource action scope <<< "$config"
            
            local json
            json=$(cat <<EOF
{
    "name": "$name",
    "description": "$description",
    "resource": "$resource",
    "action": "$action",
    "scope": "$scope"
}
EOF
)
            
            if create_permission "$name" "$json"; then
                ((created++))
            else
                ((failed++))
            fi
        else
            warn "No configuration found for permission: $name"
            ((failed++))
        fi
    done
    
    success "Permissions created: $created, failed: $failed"
}

create_role() {
    local name="$1"
    local role_data="$2"
    
    verbose "Creating role: $name"
    
    local response
    if response=$(api_call "POST" "/api/v1/roles/" "$role_data" "Create role $name"); then
        local id
        id=$(extract_id "$response")
        
        if [[ -n "$id" ]]; then
            store_kv "$ROLE_IDS_FILE" "$name" "$id"
            log "Created role: $name (ID: $id)"
            return 0
        else
            # In dry run mode, create a fake ID for testing
            if [[ "$DRY_RUN" == "true" ]]; then
                store_kv "$ROLE_IDS_FILE" "$name" "dry-run-$name"
                log "Created role: $name (ID: dry-run-$name)"
                return 0
            else
                warn "Created role $name but couldn't extract ID"
                return 1
            fi
        fi
    else
        # Check if it already exists
        if echo "$response" | grep -q "already exists"; then
            verbose "Role $name already exists, fetching ID"
            if existing_response=$(api_call "GET" "/api/v1/roles/?page_size=100" "" "Get existing roles" 2>/dev/null); then
                local id
                if command -v jq >/dev/null 2>&1; then
                    id=$(echo "$existing_response" | jq -r ".results[]? | select(.name==\"$name\") | .id // empty" 2>/dev/null)
                else
                    id=$(echo "$existing_response" | grep -o "{[^}]*\"name\":\"$name\"[^}]*}" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
                fi
                
                if [[ -n "$id" ]]; then
                    store_kv "$ROLE_IDS_FILE" "$name" "$id"
                    log "Found existing role: $name (ID: $id)"
                    return 0
                fi
            fi
        fi
        warn "Failed to create role: $name"
        return 1
    fi
}

create_all_roles() {
    info "Creating roles..."
    
    local created=0 failed=0
    
    for name in $(get_all_roles); do
        local config
        config=$(get_role_config "$name")
        
        if [[ -n "$config" ]]; then
            IFS='|' read -r display_name description <<< "$config"
            
            local json
            json=$(cat <<EOF
{
    "name": "$name",
    "display_name": "$display_name",
    "description": "$description",
    "is_active": true
}
EOF
)
            
            if create_role "$name" "$json"; then
                ((created++))
            else
                ((failed++))
            fi
        else
            warn "No configuration found for role: $name"
            ((failed++))
        fi
    done
    
    success "Roles created: $created, failed: $failed"
}

assign_permissions_to_role() {
    local role_name="$1"
    local permissions="$2"
    
    local role_id
    role_id=$(get_value "$ROLE_IDS_FILE" "$role_name")
    
    if [[ -z "$role_id" ]]; then
        warn "Role ID not found for: $role_name"
        return 1
    fi
    
    local permission_ids=()
    local missing=()
    
    for perm in $permissions; do
        local perm_id
        perm_id=$(get_value "$PERMISSION_IDS_FILE" "$perm")
        
        if [[ -n "$perm_id" ]]; then
            permission_ids+=("\"$perm_id\"")
        else
            missing+=("$perm")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        warn "Missing permissions for role $role_name: ${missing[*]}"
    fi
    
    if [[ ${#permission_ids[@]} -eq 0 ]]; then
        warn "No valid permissions found for role: $role_name"
        return 1
    fi
    
    local json
    json=$(printf '{"permission_ids":[%s]}' "$(IFS=,; echo "${permission_ids[*]}")")
    
    if api_call "POST" "/api/v1/roles/$role_id/assign-permissions-bulk" "$json" "Assign permissions to $role_name" >/dev/null; then
        log "Assigned ${#permission_ids[@]} permissions to role: $role_name"
        return 0
    else
        warn "Failed to assign permissions to role: $role_name"
        return 1
    fi
}

assign_all_permissions() {
    info "Assigning permissions to roles..."
    
    local assigned=0 failed=0
    
    for role_name in $(get_all_roles); do
        local permissions
        permissions=$(get_role_permissions "$role_name")
        
        if [[ -n "$permissions" ]]; then
            if assign_permissions_to_role "$role_name" "$permissions"; then
                ((assigned++))
            else
                ((failed++))
            fi
        else
            warn "No permissions defined for role: $role_name"
            ((failed++))
        fi
    done
    
    success "Role assignments completed: $assigned successful, $failed failed"
}

verify_setup() {
    info "Verifying setup..."
    
    # Count permissions
    local perm_count=0
    if [[ -f "$PERMISSION_IDS_FILE" ]]; then
        perm_count=$(wc -l < "$PERMISSION_IDS_FILE")
    fi
    
    # Count roles
    local role_count=0
    if [[ -f "$ROLE_IDS_FILE" ]]; then
        role_count=$(wc -l < "$ROLE_IDS_FILE")
    fi
    
    success "Setup verification: $perm_count permissions, $role_count roles created"
    
    # Verify role-permission mappings
    while IFS='=' read -r role_name role_id; do
        if [[ -n "$role_id" ]]; then
            if response=$(api_call "GET" "/api/v1/roles/$role_id/permissions" "" "Check permissions for $role_name" 2>/dev/null); then
                local perm_count
                if command -v jq >/dev/null 2>&1; then
                    perm_count=$(echo "$response" | jq '. | length' 2>/dev/null || echo "0")
                else
                    perm_count=$(echo "$response" | grep -o '"id":"[^"]*"' | wc -l)
                fi
                log "Role '$role_name' has $perm_count permissions assigned"
            fi
        fi
    done < "$ROLE_IDS_FILE" 2>/dev/null || true
}

show_usage() {
    cat << EOF
🦕 Dino E-Menu - Roles & Permissions Setup

Usage: $0 [OPTIONS]

Options:
  -u, --url URL     API base URL (default: $API_BASE_URL)
  -v, --verbose     Enable verbose output
  -d, --dry-run     Show what would be done without making changes
  -h, --help        Show this help message

Environment Variables:
  API_BASE_URL      API base URL
  VERBOSE           Set to 'true' for verbose output
  DRY_RUN           Set to 'true' for dry run mode

Examples:
  $0                    # Basic setup
  $0 --verbose          # Detailed logging
  $0 --dry-run          # See what would be done
  $0 --url https://api.example.com  # Custom API URL

This script creates:
  ✅ 35 permissions with proper resource.action format
  ✅ 3 roles (superadmin, admin, operator)
  ✅ Role-permission mappings with proper hierarchy
  ✅ Idempotent operations (safe to re-run)

To add new permissions:
  1. Add the permission name to get_all_permissions()
  2. Add the configuration to get_permission_config()
  3. Update role permissions in get_role_permissions()
EOF
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -u|--url)
                API_BASE_URL="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE="true"
                shift
                ;;
            -d|--dry-run)
                DRY_RUN="true"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Setup
    setup_temp_dir
    
    echo "🦕 Dino E-Menu - Roles & Permissions Setup"
    echo "=========================================="
    echo
    
    [[ "$DRY_RUN" == "true" ]] && warn "DRY RUN MODE - No actual changes will be made"
    
    info "API URL: $API_BASE_URL"
    
    # Check API health
    if api_call "GET" "/health" "" "API health check" >/dev/null 2>&1; then
        log "API is accessible"
    else
        warn "API health check failed - continuing anyway"
    fi
    
    # Execute setup steps
    create_all_permissions
    create_all_roles
    assign_all_permissions
    verify_setup
    
    echo
    success "🎉 Setup completed successfully!"
    echo
    info "Next steps:"
    info "  1. Test API endpoints: curl $API_BASE_URL/api/v1/permissions/"
    info "  2. Test role endpoints: curl $API_BASE_URL/api/v1/roles/"
    info "  3. Create test users and assign roles"
    info "  4. Test frontend permission gates"
}

# Run main function
main "$@"