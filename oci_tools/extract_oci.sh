#!/bin/bash
# ======================================================================
# OCI Extraction Script (v0.0.1xg - 2025/11/20)
# extract_oci.sh
#
# Downloads an OCI image via skopeo or uses existing layers
# to extract the rootfs.
# ======================================================================

# Strict error handling: Exit on error, exit on unset variable.
set -eu

# --- Global Variables ---
PURGE_LAYERS=0
RUN_SEARCH="" 
RUN_INSPECT=0
RUN_VERIFY=0
QUIET_MODE=0
SOURCE_IMAGE=""
LAYERS_DIR_INPUT="" 
DEST_DIR_RAW=""
LAYERS_DIR=""
DEST_DIR="" 
MODE=""
LAYER_EXTRACTION_STATUS=0 # Status tracker for the extraction subshell

# Function to print messages based on quiet mode
log() {
    if [ "$QUIET_MODE" -eq 0 ]; then
        echo "$@"
    fi
}

# --- Tool Check Function ---
check_dependencies() {
    local required_tools=("tar" "jq" "find")
    local missing_tools=()

    if [ "$MODE" == "DOWNLOAD" ]; then
        required_tools+=("skopeo")
    fi
    if [ "$RUN_VERIFY" -eq 1 ]; then
        required_tools+=("sha256sum")
    fi
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo "ERROR: The following critical tool(s) are missing:" >&2
        echo "           ${missing_tools[*]}" >&2
        echo "           Please install them to proceed." >&2
        exit 1
    fi
}

# --- Search Function (Parallel Find) ---
# SECURITY FIX: The pattern is escaped before being used in find -regex
search_files() {
    local search_dir="$1"
    local pattern="$2"
    
    log ""
    log "--- Search Results (Parallel Find) ---"
    
    # Escape the pattern for safe use within the regex flag of find
    local escaped_pattern
    escaped_pattern=$(printf '%s' "$pattern" | sed "s/'/'\\\''/g")

    log "Searching filenames recursively in $search_dir for escaped pattern: '$escaped_pattern'"
    
    local CPUS
    CPUS=$(nproc 2>/dev/null || echo 4)

    log "Using $CPUS parallel worker(s) for output processing."
    
    # Use eval to allow safe execution of the escaped pattern string within quotes
    find -L "$search_dir" -regextype posix-extended -regex ".*${escaped_pattern}.*" -print0 2>/dev/null |
    xargs -0 -P "$CPUS" -I {} echo {} || true
    
    log "---------------------------"
}

# --- Inspection Function ---
# Modified to use conditional logic within jq to gracefully handle null/missing arrays and objects.
inspect_metadata() {
    local config_path="$1"
    log ""
    log "--- Image Metadata Inspection ---"
    
    # Simple value lookups
    log "Architecture:   $(jq -r '.architecture' "$config_path")"
    log "OS:             $(jq -r '.os' "$config_path")"
    
    # User & WorkingDir (Using // "N/A" fallback)
    log "User:           $(jq -r '.config.User // "N/A"' "$config_path")"
    log "Working Dir:    $(jq -r '.config.WorkingDir // "N/A"' "$config_path")"
    
    # Entrypoint (Checks if Entrypoint is a non-empty array, otherwise outputs N/A)
    log "Entrypoint:     $(jq -r '.config.Entrypoint | if type == "array" and length > 0 then join(" ") else "N/A" end' "$config_path")"
    
    # CMD (Checks if Cmd is a non-empty array, otherwise outputs N/A)
    log "CMD:            $(jq -r '.config.Cmd | if type == "array" and length > 0 then join(" ") else "N/A" end' "$config_path")"
    
    # Exposed Ports (Checks if ExposedPorts exists and has keys, otherwise outputs N/A)
    log "Exposed Ports:  $(jq -r '.config.ExposedPorts | if . == null then "N/A" else (keys | join(", ")) end' "$config_path")"
    
    log "---------------------------------"
}

# --- Verification Function ---
verify_integrity() {
    local manifest_path="$1"
    local layers_dir="$2"
    
    log ""
    log "--- Content Integrity Verification ---"
    local exit_code=0
    
    jq -r '.layers[] | "\(.digest) \(.digest | split(":")[1])"' "$manifest_path" | while read -r DIGEST SHA; do
        LAYER_FILE="$layers_dir/$SHA"
        
        # Check for common extensions
        if [[ ! -f "$LAYER_FILE" ]] && [[ -f "${LAYER_FILE}.tar" ]]; then
            LAYER_FILE="${LAYER_FILE}.tar"
        elif [[ ! -f "$LAYER_FILE" ]] && [[ -f "${LAYER_FILE}.tar.gz" ]]; then
            LAYER_FILE="${LAYER_FILE}.tar.gz"
        fi
        
        if [ ! -f "$LAYER_FILE" ]; then
            echo "ERROR: Missing layer file for digest $DIGEST." >&2
            exit_code=1
            continue
        fi

        log "Verifying ${LAYER_FILE##*/}..."
        
        CALCULATED_DIGEST=$(sha256sum "$LAYER_FILE" | awk '{print "sha256:"$1}')
        
        if [ "$CALCULATED_DIGEST" = "$DIGEST" ]; then
            log "  [PASS] Digest matched: $DIGEST"
        else
            echo "  [FAIL] Calculated: $CALCULATED_DIGEST" >&2
            echo "         Expected: $DIGEST" >&2
            exit_code=1
        fi
    done
    
    if [ $exit_code -ne 0 ]; then
        return 1
    fi
    log "Verification complete."
    log "--------------------------------------"
    return 0
}

# --- Help/Examples Functions (omitted for brevity) ---
show_help() {
    echo "Usage: $0 <MODE_OPTIONS> --target-dir <DEST_DIR> [GENERAL_OPTIONS]"
    echo ""; echo "This script downloads an OCI image via 'skopeo' or uses existing layers to extract the"
    echo "root filesystem, providing advanced analysis features."; echo ""; echo "--- MODE OPTIONS (Choose ONE) ---"
    echo "  --image <SOURCE_IMAGE>    : Specifies the image to download and extract.";
    echo "  --layer-dir <LAYERS_DIR>  : Specifies an existing directory containing the layers and manifest.json (skips download).";
    echo ""; echo "--- REQUIRED OPTION ---"
    echo "  --target-dir <DEST_DIR>   : The final, local directory where the merged filesystem will be extracted.";
    echo ""; echo "--- GENERAL OPTIONS ---"
    echo "  --purge-layer-dir         : Automatically delete the layers directory after successful extraction.";
    echo "  --inspect                 : Prints key image metadata (CMD, ENV, Ports, etc.) from the image configuration file.";
    echo "  --verify                  : Calculates SHA256 hashes of all layer files and compares them against the digests.";
    echo "  --search <regexp>         : Runs a parallel recursive **filename/path search** using 'find'.";
    echo "  --quiet                   : Suppress all phase and layer messages, printing only errors and the final result.";
    echo "  --examples                : Show detailed usage examples."; echo ""
}
show_examples() {
    echo "--- Usage Examples ---"; echo ""; echo "1. Basic Download, Extraction, and Cleanup:";
    echo "./extract_oci.sh \\"; echo "  --image docker://node:20-alpine \\"; echo "  --target-dir ./node_rootfs \\"; echo "  --purge-layer-dir"; echo "";
    echo "2. Local Image Extraction with Search:"; echo "./extract_oci.sh \\"; echo "  --image my_app:v1.2 \\"; echo "  --target-dir ./app_fs \\"; echo "  --search '.*\/etc\/nginx\.conf$'"; echo ""
    echo "3. Inspection and Verification (No Extraction Focus):"; echo "./extract_oci.sh \\"; echo "  --image docker://ubuntu:22.04 \\"; echo "  --target-dir ./temp_output \\"; echo "  --inspect \\"; echo "  --verify \\"; echo "  --purge-layer-dir"; echo ""
    echo "4. Reusing Existing Layers (Debugging/Efficiency):"; echo "./extract_oci.sh \\"; echo "  --layer-dir ./busybox_layers \\"; echo "  --target-dir ./extracted_busybox_fs \\"
    echo "  --quiet"; echo ""
    echo "5. Quiet Mode for Automation (Extract and Search):"; echo "EXTRACT_PATH=\"./large_app_root\""; echo "./extract_oci.sh \\"; echo "  --image large_app:2.0 \\"; echo "  --target-dir \"\$EXTRACT_PATH\" \\"; echo "  --search '.*license.*' \\"; echo "  --quiet"
}


# --- Argument Parsing (omitted for brevity) ---
while [ "$#" -gt 0 ]; do
    case "$1" in
        --help) show_help; exit 0 ;; --examples) show_examples; exit 0 ;; --purge-layer-dir) PURGE_LAYERS=1; shift ;;
        --inspect) RUN_INSPECT=1; shift ;; --verify) RUN_VERIFY=1; shift ;; --quiet) QUIET_MODE=1; shift ;;
        --search)
            if [ -z "$2" ]; then echo "ERROR: --search requires a regular expression pattern." >&2; exit 1; fi
            RUN_SEARCH="$2"; shift 2 ;;
        --image) SOURCE_IMAGE="$2"; shift 2 ;; --layer-dir) LAYERS_DIR_INPUT="$2"; shift 2 ;;
        --target-dir) DEST_DIR_RAW="$2"; shift 2 ;;
        *) echo "ERROR: Unknown option or invalid argument: $1" >&2; echo "Use '$0 --help' for usage." >&2; exit 1 ;;
    esac
done

# --- Validation and Setup ---
if [ -n "$SOURCE_IMAGE" ] && [ -n "$LAYERS_DIR_INPUT" ]; then echo "ERROR: Cannot use both --image and --layer-dir simultaneously." >&2; exit 1
elif [ -z "$DEST_DIR_RAW" ]; then echo "ERROR: --target-dir is required for all operations." >&2; exit 1; fi

if [ -n "$LAYERS_DIR_INPUT" ]; then MODE="EXISTING"; LAYERS_DIR="$LAYERS_DIR_INPUT"; PURGE_LAYERS=0 
else MODE="DOWNLOAD"; LAYERS_DIR=$(mktemp -d --tmpdir=/tmp oci_extract_XXXXXX); fi
DEST_DIR_ABS="$DEST_DIR_RAW"

# --- Tool Checks (Early Exit) ---
check_dependencies

# --- Global Setup (Cleanup) ---
cleanup() {
    local exit_code=$?
    # Set the extraction status if it was set by the subshell, otherwise use the current exit_code
    if [ "$LAYER_EXTRACTION_STATUS" -ne 0 ] && [ "$exit_code" -eq 0 ]; then
        exit_code="$LAYER_EXTRACTION_STATUS"
    fi

    if [ "$MODE" == "DOWNLOAD" ] && [ $PURGE_LAYERS -eq 1 ] && [ -d "$LAYERS_DIR" ]; then
        log "Removing temporary layers directory: $LAYERS_DIR"
        rm -rf "$LAYERS_DIR" 
    elif [ $exit_code -ne 0 ] && [ "$MODE" == "DOWNLOAD" ] && [ -d "$LAYERS_DIR" ]; then
        echo "Script failed with code $exit_code. Layer files left at: $LAYERS_DIR" >&2
    fi
    trap - EXIT 
    exit "$exit_code"
}
if [ "$MODE" == "DOWNLOAD" ]; then
    trap cleanup EXIT INT TERM
fi


# --- Phase 1: Image Source ---
if [ "$MODE" == "DOWNLOAD" ]; then
    log "--- Phase 1: Downloading Image Layers ---"
    log "Temporary Layers Directory: $LAYERS_DIR"

    if [[ "$SOURCE_IMAGE" != *"://"* ]]; then
        SKOPEO_SOURCE="docker-daemon:$SOURCE_IMAGE"
    else
        SKOPEO_SOURCE="$SOURCE_IMAGE"
    fi

    log "Source Image: $SKOPEO_SOURCE"
    skopeo copy --insecure-policy "$SKOPEO_SOURCE" "dir:$LAYERS_DIR"
    
    log "--- Phase 1 Complete ---"
else # MODE == EXISTING
    log "--- Phase 1: Using Existing Layers ---"
    log "Source Layers Directory: $LAYERS_DIR"
    
    if [ ! -d "$LAYERS_DIR" ]; then
        echo "ERROR: Existing layers directory '$LAYERS_DIR' not found." >&2
        exit 1
    fi
    log "--- Phase 1 Complete ---"
fi


# Resolve absolute path for layers
LAYERS_DIR=$(realpath "$LAYERS_DIR")
MANIFEST_PATH="$LAYERS_DIR/manifest.json"

# --- Phase 1.5: Verification and Inspection (Pre-Extraction) ---

if [ ! -f "$MANIFEST_PATH" ]; then
    echo "ERROR: manifest.json not found in '$LAYERS_DIR'. Directory is not a valid OCI layer output." >&2
    exit 1
fi

CONFIG_FILE_DIGEST=$(jq -r '.config.digest | split(":")[1]' "$MANIFEST_PATH")
CONFIG_PATH="$LAYERS_DIR/$CONFIG_FILE_DIGEST"
if [ ! -f "$CONFIG_PATH" ]; then
    echo "ERROR: Configuration file '$CONFIG_FILE_DIGEST' not found." >&2
    exit 1
fi

if [ "$RUN_VERIFY" -eq 1 ]; then
    verify_integrity "$MANIFEST_PATH" "$LAYERS_DIR"
fi

if [ "$RUN_INSPECT" -eq 1 ]; then
    inspect_metadata "$CONFIG_PATH"
fi

# --- Phase 2: Layer Extraction ---
log ""
log "--- Phase 2: Layer Extraction ---"

# 2.1 Destination Safety Check
if [ -d "$DEST_DIR_RAW" ]; then
    if [ -n "$(ls -A "$DEST_DIR_RAW")" ]; then
        echo "ERROR: Destination directory '$DEST_DIR_RAW' exists and is NOT empty. Aborting extraction." >&2
        exit 1
    fi
    log "Warning: Destination directory '$DEST_DIR_RAW' already exists but is empty. Proceeding."
else
    mkdir -p "$DEST_DIR_RAW"
fi

# Resolve the absolute path
DEST_DIR=$(realpath "$DEST_DIR_RAW")

log "Extraction Target: $DEST_DIR"
log "Starting layer merging..."

# 2.2 Extraction Loop (Layer Mapping and Subshell Exit Capture)
( # Start subshell to reliably capture the exit status of the pipeline
    # Iterate over the 'diff_ids' (uncompressed SHA) from the config file.
    jq -r '.rootfs.diff_ids[]' "$CONFIG_PATH" | while read -r DIFF_ID; do
        
        # Get the index of the Diff ID in the config file
        LAYER_INDEX=$(jq -r --arg DIFF_ID "$DIFF_ID" '.rootfs.diff_ids | index($DIFF_ID)' "$CONFIG_PATH")

        # Get the layer digest (which is the filename) at the same index in the manifest file
        LAYER_DIGEST=$(jq -r --arg INDEX "$LAYER_INDEX" '.layers[($INDEX | tonumber)].digest' "$MANIFEST_PATH")

        # Extract the SHA part from the digest (e.g., sha256:1234... -> 1234...)
        LAYER_SHA=$(echo "$LAYER_DIGEST" | cut -d ':' -f 2)
        
        if [ -z "$LAYER_SHA" ]; then
            echo "ERROR: Failed to map Diff ID $DIFF_ID (at index $LAYER_INDEX) to a blob digest in the manifest." >&2
            exit 1 
        fi

        LAYER_FILE="$LAYERS_DIR/$LAYER_SHA"
        
        # Check for layer file with common extensions
        if [[ -f "$LAYER_FILE" ]]; then TARGET_FILE="$LAYER_FILE";
        elif [[ -f "${LAYER_FILE}.tar" ]]; then TARGET_FILE="${LAYER_FILE}.tar";
        elif [[ -f "${LAYER_FILE}.tar.gz" ]]; then TARGET_FILE="${LAYER_FILE}.tar.gz";
        else
            echo "ERROR: Layer file for SHA '$LAYER_SHA' (mapped from Diff ID $DIFF_ID) not found. This indicates an incomplete layer directory." >&2
            exit 1 
        fi

        log "Applying layer: ${TARGET_FILE##*/}"
        
        # tar -xf: extracts file, -C: changes directory to merge contents
        tar -xf "$TARGET_FILE" -C "$DEST_DIR"
        
        if [ $? -ne 0 ]; then
            echo "ERROR: tar extraction failed for ${TARGET_FILE##*/}. Aborting." >&2
            exit 1 # Exit subshell on failure
        fi
    done
    exit 0 # Ensure the subshell exits cleanly if the loop completes successfully
)
# Capture exit status of the subshell
LAYER_EXTRACTION_STATUS=$?

if [ "$LAYER_EXTRACTION_STATUS" -ne 0 ]; then
    echo "ERROR: Layer extraction process failed (Exit Code $LAYER_EXTRACTION_STATUS). Aborting script." >&2
    exit 1
fi

log "--- Phase 2 Complete ---"
log "Extraction complete. Files are in $DEST_DIR"

# --- Phase 3: Search ---
if [ -n "$RUN_SEARCH" ]; then
    search_files "$DEST_DIR" "$RUN_SEARCH"
fi
# --- End of Phase 3 ---

if [ "$MODE" == "DOWNLOAD" ]; then
    log "NOTE: Layers are stored in $LAYERS_DIR. Use --purge-layer-dir to automatically delete them."
fi
