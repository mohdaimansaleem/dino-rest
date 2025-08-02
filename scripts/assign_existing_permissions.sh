#!/bin/bash

# =============================================================================
# Dino E-Menu API - Assign Existing Permissions to Roles
# =============================================================================
# This script fetches existing permissions and roles, then assigns them properly
# =============================================================================

set -euo pipefail

# Configuration
readonly API_BASE_URL="${API_BASE_URL:-https://dino-backend-api-1018711634531.us-central1.run.app}"
VERBOSE="${VERBOSE:-false}"

# Colors
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# Logging functions
log() { echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $*${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $*${NC}" >&2; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $*${NC}" >&2; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] ℹ️  $*${NC}"; }
success() { echo -e "${CYAN}[$(date +'%H:%M:%S')] 🎉 $*${NC}"; }
verbose() { [[ "$VERBOSE" == "true" ]] && echo -e "${BLUE}[$(date +'%H:%M:%S')] 🔍 $*${NC}"; }

# Get auth token
get_auth_token() {
    if command -v gcloud >/dev/null 2>&1; then
        gcloud auth print-identity-token 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# Make API call
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    
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
    
    if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
        echo "$body"
        return 0
    else
        error "API call failed (HTTP $http_code): $body"
        return 1
    fi
}

# Fetch all permissions
fetch_permissions() {
    info "Fetching existing permissions..."
    
    local response
    if response=$(api_call "GET" "/api/v1/permissions/?page_size=100"); then
        if command -v jq >/dev/null 2>&1; then
            echo "$response" | jq -r '.results[] | "\(.name)=\(.id)"' 2>/dev/null
        else
            # Fallback parsing without jq
            echo "$response" | grep -o '"name":"[^"]*","[^"]*":"[^"]*","[^"]*":"[^"]*","[^"]*":"[^"]*","id":"[^"]*"' | \
            sed 's/"name":"\([^"]*\)".*"id":"\([^"]*\)"/\1=\2/'
        fi
    else
        error "Failed to fetch permissions"
        return 1
    fi
}

# Fetch all roles
fetch_roles() {
    info "Fetching existing roles..."
    
    local response
    if response=$(api_call "GET" "/api/v1/roles/?page_size=100"); then
        if command -v jq >/dev/null 2>&1; then
            echo "$response" | jq -r '.results[] | "\(.name)=\(.id)"' 2>/dev/null
        else
            # Fallback parsing without jq
            echo "$response" | grep -o '"name":"[^"]*"[^}]*"id":"[^"]*"' | \
            sed 's/"name":"\([^"]*\)".*"id":"\([^"]*\)"/\1=\2/'
        fi
    else
        error "Failed to fetch roles"
        return 1
    fi
}

# Assign permissions to role
assign_permissions() {
    local role_name="$1"
    local role_id="$2"
    shift 2
    local permission_ids=("$@")
    
    if [[ ${#permission_ids[@]} -eq 0 ]]; then
        warn "No permissions to assign to role: $role_name"
        return 1
    fi
    
    local json
    json=$(printf '{"permission_ids":[%s]}' "$(IFS=,; echo "${permission_ids[*]}")")
    
    verbose "Assigning ${#permission_ids[@]} permissions to $role_name"
    verbose "JSON: $json"
    
    if api_call "POST" "/api/v1/roles/$role_id/assign-permissions-bulk" "$json" >/dev/null; then
        log "Assigned ${#permission_ids[@]} permissions to role: $role_name"
        return 0
    else
        warn "Failed to assign permissions to role: $role_name"
        return 1
    fi
}

main() {
    echo "🦕 Dino E-Menu - Assign Existing Permissions"
    echo "============================================"
    echo
    
    info "API URL: $API_BASE_URL"
    
    # Fetch existing data
    local permissions_data roles_data
    permissions_data=$(fetch_permissions) || exit 1
    roles_data=$(fetch_roles) || exit 1
    
    # Parse permissions into associative arrays
    declare -A permission_ids
    while IFS='=' read -r name id; do
        [[ -n "$name" && -n "$id" ]] && permission_ids["$name"]="$id"
    done <<< "$permissions_data"
    
    # Parse roles
    declare -A role_ids
    while IFS='=' read -r name id; do
        [[ -n "$name" && -n "$id" ]] && role_ids["$name"]="$id"
    done <<< "$roles_data"
    
    info "Found ${#permission_ids[@]} permissions and ${#role_ids[@]} roles"
    
    # Define role permissions (using only existing permissions)
    local superadmin_perms=(
        "workspace.read" "workspace.create" "workspace.update" "workspace.delete" "workspace.manage"
        "venue.read" "venue.create" "venue.update" "venue.delete" "venue.manage"
        "menu.read" "menu.create" "menu.update" "menu.delete" "menu.manage"
        "order.read" "order.create" "order.update" "order.delete" "order.manage"
        "table.read" "table.create" "table.update" "table.delete" "table.manage"
        "user.read" "user.create" "user.update" "user.delete" "user.manage"
        "analytics.read" "analytics.manage"
    )
    
    local admin_perms=(
        "workspace.read" "workspace.create" "workspace.update" "workspace.delete" "workspace.manage"
        "venue.read" "venue.create" "venue.update" "venue.delete" "venue.manage"
        "menu.read" "menu.create" "menu.update" "menu.delete" "menu.manage"
        "order.read" "order.create" "order.update" "order.delete" "order.manage"
        "user.read" "user.create" "user.update" "user.delete" "user.manage"
        "table.read" "table.create" "table.update" "table.delete" "table.manage"
        "analytics.read" "analytics.manage"
    )
    
    local operator_perms=(
        "workspace.read"
        "venue.read"
        "menu.read"
        "order.read" "order.create" "order.update"
        "user.read"
        "table.read" "table.update"
        "analytics.read"
    )
    
    # Assign permissions to roles
    info "Assigning permissions to roles..."
    
    # SuperAdmin
    if [[ -n "${role_ids[superadmin]:-}" ]]; then
        local superadmin_ids=()
        for perm in "${superadmin_perms[@]}"; do
            [[ -n "${permission_ids[$perm]:-}" ]] && superadmin_ids+=("\"${permission_ids[$perm]}\"")
        done
        assign_permissions "superadmin" "${role_ids[superadmin]}" "${superadmin_ids[@]}"
    else
        warn "SuperAdmin role not found"
    fi
    
    # Admin
    if [[ -n "${role_ids[admin]:-}" ]]; then
        local admin_ids=()
        for perm in "${admin_perms[@]}"; do
            [[ -n "${permission_ids[$perm]:-}" ]] && admin_ids+=("\"${permission_ids[$perm]}\"")
        done
        assign_permissions "admin" "${role_ids[admin]}" "${admin_ids[@]}"
    else
        warn "Admin role not found"
    fi
    
    # Operator
    if [[ -n "${role_ids[operator]:-}" ]]; then
        local operator_ids=()
        for perm in "${operator_perms[@]}"; do
            [[ -n "${permission_ids[$perm]:-}" ]] && operator_ids+=("\"${permission_ids[$perm]}\"")
        done
        assign_permissions "operator" "${role_ids[operator]}" "${operator_ids[@]}"
    else
        warn "Operator role not found"
    fi
    
    echo
    success "🎉 Permission assignment completed!"
    echo
    info "Next steps:"
    info "  1. Verify assignments: curl $API_BASE_URL/api/v1/roles/"
    info "  2. Test with users and frontend"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--verbose] [--help]"
            echo "Assigns existing permissions to existing roles"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

main "$@"