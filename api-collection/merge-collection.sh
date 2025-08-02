#!/bin/bash

# =============================================================================
# Dino E-Menu API Collection Merger
# =============================================================================
# This script merges all API collection chunks into a single Postman collection
# Usage: ./merge-collection.sh
# Output: dino-emenu-api-collection.json
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌ ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] ℹ️  INFO: $1${NC}"
}

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="dino-emenu-api-collection.json"
TEMP_FILE="temp-collection.json"

# Collection chunk files in order
COLLECTION_FILES=(
    "00-collection-header.json"
    "01-authentication.json"
    "02-users.json"
    "03-workspaces.json"
    "04-venues.json"
    "05-menu.json"
    "06-tables.json"
    "07-orders.json"
    "08-roles.json"
    "09-permissions.json"
    "10-health.json"
    "11-collection-footer.json"
)

# =============================================================================
# VALIDATION
# =============================================================================

validate_files() {
    info "Validating collection chunk files..."
    
    local missing_files=()
    
    for file in "${COLLECTION_FILES[@]}"; do
        if [ ! -f "$SCRIPT_DIR/$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        error "Missing collection files:"
        for file in "${missing_files[@]}"; do
            error "  - $file"
        done
        exit 1
    fi
    
    log "All collection files found"
}

# =============================================================================
# MERGE PROCESS
# =============================================================================

merge_collection() {
    info "Merging collection files..."
    
    # Remove existing output and temp files
    [ -f "$SCRIPT_DIR/$OUTPUT_FILE" ] && rm "$SCRIPT_DIR/$OUTPUT_FILE"
    [ -f "$SCRIPT_DIR/$TEMP_FILE" ] && rm "$SCRIPT_DIR/$TEMP_FILE"
    
    # Start merging
    local file_count=0
    
    for file in "${COLLECTION_FILES[@]}"; do
        info "Processing: $file"
        
        if [ $file_count -eq 0 ]; then
            # First file - copy as is
            cp "$SCRIPT_DIR/$file" "$SCRIPT_DIR/$TEMP_FILE"
        else
            # Append content (remove first and last lines for JSON structure)
            if [[ "$file" == *"footer"* ]]; then
                # Footer file - just append
                cat "$SCRIPT_DIR/$file" >> "$SCRIPT_DIR/$TEMP_FILE"
            else
                # Regular file - append content
                cat "$SCRIPT_DIR/$file" >> "$SCRIPT_DIR/$TEMP_FILE"
            fi
        fi
        
        file_count=$((file_count + 1))
    done
    
    # Move temp file to final output
    mv "$SCRIPT_DIR/$TEMP_FILE" "$SCRIPT_DIR/$OUTPUT_FILE"
    
    log "Collection merged successfully"
}

# =============================================================================
# VALIDATION AND FORMATTING
# =============================================================================

validate_json() {
    info "Validating JSON structure..."
    
    # Check if jq is available for validation
    if command -v jq >/dev/null 2>&1; then
        if jq empty "$SCRIPT_DIR/$OUTPUT_FILE" 2>/dev/null; then
            log "JSON structure is valid"
            
            # Pretty format the JSON
            jq . "$SCRIPT_DIR/$OUTPUT_FILE" > "$SCRIPT_DIR/$TEMP_FILE"
            mv "$SCRIPT_DIR/$TEMP_FILE" "$SCRIPT_DIR/$OUTPUT_FILE"
            log "JSON formatted successfully"
        else
            error "Invalid JSON structure in merged collection"
            return 1
        fi
    else
        warn "jq not available - skipping JSON validation and formatting"
    fi
}

# =============================================================================
# STATISTICS
# =============================================================================

generate_statistics() {
    info "Generating collection statistics..."
    
    local file_size=$(du -h "$SCRIPT_DIR/$OUTPUT_FILE" | cut -f1)
    local line_count=$(wc -l < "$SCRIPT_DIR/$OUTPUT_FILE")
    
    echo ""
    echo "📊 Collection Statistics:"
    echo "  📁 Output file: $OUTPUT_FILE"
    echo "  📏 File size: $file_size"
    echo "  📄 Lines: $line_count"
    echo "  🔗 Source files: ${#COLLECTION_FILES[@]}"
    
    # Count endpoints if jq is available
    if command -v jq >/dev/null 2>&1; then
        local endpoint_count=$(jq '[.item[].item[]] | length' "$SCRIPT_DIR/$OUTPUT_FILE" 2>/dev/null || echo "unknown")
        local folder_count=$(jq '.item | length' "$SCRIPT_DIR/$OUTPUT_FILE" 2>/dev/null || echo "unknown")
        echo "  📂 Folders: $folder_count"
        echo "  🔗 Total endpoints: $endpoint_count"
    fi
    
    echo ""
}

# =============================================================================
# USAGE INSTRUCTIONS
# =============================================================================

show_usage_instructions() {
    echo ""
    echo "🎉 Collection merge completed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "  1. Import the collection into Postman:"
    echo "     - Open Postman"
    echo "     - Click 'Import'"
    echo "     - Select '$OUTPUT_FILE'"
    echo ""
    echo "  2. Set up environment variables:"
    echo "     - Create a new environment in Postman"
    echo "     - Add these variables:"
    echo "       • base_url: http://localhost:8080 (or your API URL)"
    echo "       • access_token: (will be auto-set after login)"
    echo "       • user_id: (will be auto-set after login)"
    echo "       • workspace_id: (set manually or auto-set)"
    echo "       • venue_id: (set manually or auto-set)"
    echo ""
    echo "  3. Test the collection:"
    echo "     - Start with 'Root Health Check' (no auth required)"
    echo "     - Register a user or login"
    echo "     - Test other endpoints"
    echo ""
    echo "  4. For production use:"
    echo "     - Update base_url to your production API"
    echo "     - Ensure proper authentication"
    echo ""
    echo "📁 Collection file: $SCRIPT_DIR/$OUTPUT_FILE"
    echo ""
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    echo "🦕 ============================================================================="
    echo "🦕 Dino E-Menu API Collection Merger"
    echo "🦕 ============================================================================="
    echo ""
    
    # Change to script directory
    cd "$SCRIPT_DIR"
    
    # Validate files exist
    validate_files
    
    # Merge collection
    merge_collection
    
    # Validate and format JSON
    validate_json
    
    # Generate statistics
    generate_statistics
    
    # Show usage instructions
    show_usage_instructions
    
    log "Collection merge process completed successfully!"
}

# Run main function
main "$@"