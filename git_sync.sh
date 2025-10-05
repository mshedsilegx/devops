#!/bin/bash

set -euo pipefail

# Function to display usage information
usage() {
    echo "Usage: $0 --sync-method={pull-only|push-only|pull-push|init-and-sync} [options...]" >&2
    echo "" >&2
    echo "Options:" >&2
    echo "  --sync-method=<method>        : Primary synchronization method." >&2
    echo "                                :   pull-only: Only pull changes from remote." >&2
    echo "                                :   push-only: Only push changes to remote." >&2
    echo "                                :   pull-push: Pull then push changes." >&2
    echo "                                :   init-and-sync: Clone repository if not exists, then sync." >&2
    echo "" >&2
    echo "  --pull-method=<method>        : Method for pulling changes (required for pull-only/pull-push)." >&2
    echo "                                :   pull: Uses 'git pull' (default merge or rebase based on git config)." >&2
    echo "                                :   fetch-merge: Fetches, then merges (creates merge commit)." >&2
    echo "                                :   fetch-rebase: Fetches, then rebases (rewrites history)." >&2
    echo "                                :   fetch-reset: Fetches, then hard resets (DANGEROUS: discards local changes)." >&2
    echo "" >&2
    echo "  --pull-strategy=<strategy>    : Strategy for 'pull' method (merge or rebase). Default: merge." >&2
    echo "" >&2
    echo "  --push-method=<method>        : Method for pushing changes (required for pull-only/pull-push)." >&2
    echo "                                :   default: Uses 'git push'." >&2
    echo "                                :   force: Uses 'git push --force-with-lease' (DANGEROUS: overwrites remote history)." >&2
    echo "                                :   set-upstream: Uses 'git push -u' to set upstream tracking." >&2
    echo "" >&2
    echo "  --dry-run                     : Print git commands instead of executing them." >&2
    echo "  --prune                       : Prune stale remote-tracking branches during fetch/pull." >&2
    echo "  --use-upstream                : Dynamically determine remote name and branch from local tracking." >&2
    echo "  --ff-only                     : Only fast-forward merge; fail if not possible (for fetch-merge)." >&2
    echo "  --atomic-push                 : Push all refs atomically (for push operations)." >&2
    echo "  --merge-commit-message=<msg>  : Custom merge commit message (for fetch-merge)." >&2
    echo "" >&2
    echo "  --repo-url=<url>              : Override GIT_REPO_URL (required for init-and-sync if not in env)." >&2
    echo "  --remote-name=<name>          : Override GIT_REMOTE_NAME (default: origin)." >&2
    echo "  --remote-branch=<branch>      : Override GIT_REMOTE_BRANCH (default: main)." >&2
    echo "  --local-dir=<path>            : Override GIT_LOCAL_DIR (target directory for clone)." >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 --sync-method=pull-push --pull-method=fetch-merge --push-method=default" >&2
    echo "  $0 --sync-method=init-and-sync --repo-url=git@github.com:user/repo.git --pull-method=fetch-rebase" >&2
    exit 1
}

log_info() {
    echo "INFO: $(date +'%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo "WARNING: $(date +'%Y-%m-%d %H:%M:%S') - $1" >&2
}

log_error() {
    echo "ERROR: $(date +'%Y-%m-%d %H:%M:%S') - $1" >&2
    exit 1
}



# ======================================================================
# Git Synchronization Script (v5 - Feature Complete)
# ----------------------------------------------------------------------
# Reads configuration from git_sync.env, environment variables, or arguments.
# Includes options for Dry Run, Prune, Use Upstream, FF-Only merge, and Fetch-Rebase.
# ======================================================================

# --- 1. Load Environment Configuration ---
ENV_FILE="git_sync.env"
if [ -f "${ENV_FILE}" ]; then
    log_info "Sourcing environment variables from ${ENV_FILE}"
    set -a
    . "${ENV_FILE}"
    set +a
else
    log_warn "Configuration file ${ENV_FILE} not found. Using defaults and environment variables."
fi

# --- 2. Initialize Configuration Variables ---
# Read from environment (which includes sourced file) or safe defaults
REPO_URL="${GIT_REPO_URL:-}"
REMOTE_NAME="${GIT_REMOTE_NAME:-origin}"
REMOTE_BRANCH="${GIT_REMOTE_BRANCH:-main}"
LOCAL_BRANCH="${GIT_LOCAL_BRANCH:-}"
LOCAL_DIR="${GIT_LOCAL_DIR:-}"

PULL_STRATEGY="${GIT_PULL_STRATEGY:-merge}"

# --- 3. Argument Parsing and Global Variables ---
SYNC_METHOD=""
PULL_METHOD=""
PUSH_METHOD=""
DRY_RUN=0
PRUNE=0
USE_UPSTREAM=0
FF_ONLY=0 # New Flag
ATOMIC_PUSH=0 # New Flag
MERGE_MESSAGE="Automated merge during git_sync.sh operation."

# Process Command-Line Arguments (Highest Priority)
for arg in "$@"; do
    case "${arg}" in
        # Primary Sync Method
        --sync-method=pull-only) SYNC_METHOD="pull-only" ;;
        --sync-method=push-only) SYNC_METHOD="push-only" ;;
        --sync-method=pull-push) SYNC_METHOD="pull-push" ;;
        --sync-method=init-and-sync) SYNC_METHOD="init-and-sync" ;;

        # Pull/Push Methods
        --pull-method=pull) PULL_METHOD="pull" ;;
        --pull-method=fetch-merge) PULL_METHOD="fetch-merge" ;;
        --pull-method=fetch-reset) PULL_METHOD="fetch-reset" ;;
        --pull-method=fetch-rebase) PULL_METHOD="fetch-rebase" ;;
        --pull-strategy=merge) PULL_STRATEGY="merge" ;;
        --pull-strategy=rebase) PULL_STRATEGY="rebase" ;;
        --push-method=default) PUSH_METHOD="default" ;;
        --push-method=force) PUSH_METHOD="force" ;;
        --push-method=set-upstream) PUSH_METHOD="set-upstream" ;;
        
        # Options
        --dry-run) DRY_RUN=1 ;;
        --prune) PRUNE=1 ;;
        --use-upstream) USE_UPSTREAM=1 ;;
        --ff-only) FF_ONLY=1 ;; # New Option
        --atomic-push) ATOMIC_PUSH=1 ;; # New Option
        --merge-commit-message=*) MERGE_MESSAGE="${arg#*=}" ;;

        # Configuration Overrides
        --repo-url=*) REPO_URL="${arg#*=}" ;;
        --remote-name=*) REMOTE_NAME="${arg#*=}" ;;
        --remote-branch=*) REMOTE_BRANCH="${arg#*=}" ;;
        --local-dir=*) LOCAL_DIR="${arg#*=}" ;;

        *)
            # Ignore other arguments
            ;;
    esac
done

# Set the command execution variable
GIT_CMD=""
if [ "${DRY_RUN}" -eq 1 ]; then
    GIT_CMD="echo git"
    log_warn "DRY RUN MODE ENABLED: Commands will be printed but NOT executed."
else
    GIT_CMD="git"
fi

# ----------------------------------------------------------------------
# --- Helper Functions ---
# ----------------------------------------------------------------------

# Function to dynamically set REMOTE_NAME and REMOTE_BRANCH based on upstream tracking
set_upstream_config() {
    if [ "${USE_UPSTREAM}" -eq 1 ]; then
        log_info "Option --use-upstream detected. Dynamically determining tracking branch..."
        local upstream_ref
        # Use a subshell to prevent set -e from exiting if rev-parse fails
        upstream_ref=$( "${GIT_CMD}" rev-parse --symbolic-full-name --abbrev-ref "${LOCAL_BRANCH}@{u}" 2>/dev/null || true )

        if [ -z "${upstream_ref}" ]; then
            log_error "Local branch '${LOCAL_BRANCH}' is not tracking any remote branch. Cannot use --use-upstream."
            # log_error exits, so return 1 is unreachable.
        fi

        local detected_remote_name=$(echo "${upstream_ref}" | cut -d/ -f1)
        local detected_remote_branch=$(echo "${upstream_ref}" | cut -d/ -f2-)

        # Check if the current local branch is actually tracking the detected upstream
        local current_tracking_info
        current_tracking_info=$( "${GIT_CMD}" rev-parse --abbrev-ref "${LOCAL_BRANCH}@{u}" 2>/dev/null || true )

        if [ "${current_tracking_info}" != "${detected_remote_name}/${detected_remote_branch}" ]; then
            log_warn "Local branch '${LOCAL_BRANCH}' is currently tracking '${current_tracking_info}', but --use-upstream detected '${detected_remote_name}/${detected_remote_branch}'.
         Proceeding with detected upstream. Consider running 'git branch --set-upstream-to=${detected_remote_name}/${detected_remote_branch}' manually."
        fi

        REMOTE_NAME="${detected_remote_name}"
        REMOTE_BRANCH="${detected_remote_branch}"
        log_info "Tracking set to: ${REMOTE_NAME}/${REMOTE_BRANCH}"
    fi
    return 0
}

# Function to perform the PULL operation
pull_operation() {
    local pull_method="$1"
    local prune_flag=""; if [ "${PRUNE}" -eq 1 ]; then prune_flag="--prune"; fi
    local merge_options=""; if [ "${FF_ONLY}" -eq 1 ]; then merge_options="--ff-only"; fi
    
    log_info "--- PULL Operation (Method: ${pull_method}) ---"

    case "${pull_method}" in
        pull)
            local pull_strategy_option=""
            if [ "${PULL_STRATEGY}" == "rebase" ]; then
                pull_strategy_option="--rebase"
            elif [ "${PULL_STRATEGY}" == "merge" ]; then
                pull_strategy_option="--no-rebase"
            else
                log_error "Invalid pull strategy '${PULL_STRATEGY}'. Must be 'merge' or 'rebase'."
                # log_error exits, so return 1 is unreachable.
            fi
            log_info "Executing: ${GIT_CMD} pull ${prune_flag} ${merge_options} ${pull_strategy_option} ${REMOTE_NAME} ${REMOTE_BRANCH}:${LOCAL_BRANCH}"
            "${GIT_CMD}" pull ${prune_flag} ${merge_options} ${pull_strategy_option} "${REMOTE_NAME}" "${REMOTE_BRANCH}":"${LOCAL_BRANCH}"
            ;;

        fetch-merge)
            log_info "Phase 1/2: Executing: ${GIT_CMD} fetch ${prune_flag} ${REMOTE_NAME} ${REMOTE_BRANCH}"
            "${GIT_CMD}" fetch ${prune_flag} "${REMOTE_NAME}" "${REMOTE_BRANCH}"

            log_info "Phase 2/2: Executing: ${GIT_CMD} merge ${merge_options} --no-edit -m "${MERGE_MESSAGE}" ${REMOTE_NAME}/${REMOTE_BRANCH}"
            # Use a subshell for merge to allow aborting without exiting due to set -e
            if ! ( "${GIT_CMD}" merge ${merge_options} --no-edit -m "${MERGE_MESSAGE}" "${REMOTE_NAME}/${REMOTE_BRANCH}" ); then
                if [ "${FF_ONLY}" -eq 1 ]; then
                    log_error "Merge failed due to --ff-only. Local branch has diverged. Resolve manually."
                else
                    log_warn "Merge failed. Attempting to abort merge to clean up..."
                    "${GIT_CMD}" merge --abort > /dev/null 2>&1 || true # true to prevent set -e from exiting if abort fails
                fi
                return 1
            fi
            ;;

        fetch-rebase)
            log_info "Phase 1/2: Executing: ${GIT_CMD} fetch ${prune_flag} ${REMOTE_NAME} ${REMOTE_BRANCH}"
            "${GIT_CMD}" fetch ${prune_flag} "${REMOTE_NAME}" "${REMOTE_BRANCH}"

            log_info "Phase 2/2: Executing: ${GIT_CMD} rebase ${REMOTE_NAME}/${REMOTE_BRANCH}"
            if ! ( "${GIT_CMD}" rebase "${REMOTE_NAME}/${REMOTE_BRANCH}" ); then
                log_error "Rebase failed. Local work is preserved. Run 'git rebase --abort' or resolve conflicts manually."
                # log_error exits, so return 1 is unreachable.
            fi
            ;;

        fetch-reset)
            log_info "Phase 1/2: Executing: ${GIT_CMD} fetch ${prune_flag} ${REMOTE_NAME} ${REMOTE_BRANCH}"
            "${GIT_CMD}" fetch ${prune_flag} "${REMOTE_NAME}" "${REMOTE_BRANCH}"
            log_info "Phase 2/2: Executing: ${GIT_CMD} reset --hard ${REMOTE_NAME}/${REMOTE_BRANCH}"
            "${GIT_CMD}" reset --hard "${REMOTE_NAME}/${REMOTE_BRANCH}"
            ;;

        *)
            log_error "Invalid pull method '${pull_method}'."
            # log_error exits, so return 1 is unreachable.
            ;;
    esac
    
    log_info "PULL Operation completed successfully."
    return 0
}

# Function to perform the PUSH operation
push_operation() {
    local push_method="$1"
    local atomic_flag=""; if [ "${ATOMIC_PUSH}" -eq 1 ]; then atomic_flag="--atomic"; fi
    log_info "--- PUSH Operation (Method: ${push_method}) ---"

    local push_options=""
    case "${push_method}" in
        default) push_options=""; ;;
        force) push_options="--force-with-lease"; log_warn "Attempting to overwrite remote history."; ;;
        set-upstream) push_options="-u"; ;;
        *) log_error "Invalid push method '${push_method}'."; # log_error exits, so return 1 is unreachable.
    esac

    log_info "Executing: ${GIT_CMD} push ${atomic_flag} ${push_options} ${REMOTE_NAME} ${LOCAL_BRANCH}:${REMOTE_BRANCH}"
    "${GIT_CMD}" push ${atomic_flag} ${push_options} "${REMOTE_NAME}" "${LOCAL_BRANCH}":"${REMOTE_BRANCH}"
    
    log_info "PUSH Operation completed successfully."
    return 0
}

# Function to perform the CLONE operation
clone_operation() {
    log_info "--- CLONE Operation ---"
    local target_dir="${LOCAL_DIR}"
    if [ -z "${target_dir}" ]; then target_dir=$(basename "${REPO_URL}" .git); fi

    if [ -d "${target_dir}" ] && [ -d "${target_dir}/.git" ]; then
        log_info "Local directory '${target_dir}' already exists and is a Git repo. Skipping clone."
        if [ -n "${LOCAL_BRANCH}" ]; then
            # Check if LOCAL_BRANCH exists in the existing repo before checking it out
            if "${GIT_CMD}" rev-parse --verify "${LOCAL_BRANCH}" >/dev/null 2>&1; then
                log_info "Checking out existing local branch '${LOCAL_BRANCH}'."
                "${GIT_CMD}" checkout "${LOCAL_BRANCH}" > /dev/null 2>&1
            else
                log_warn "Local branch '${LOCAL_BRANCH}' does not exist in '${target_dir}'. Staying on current branch."
            fi
        fi
        cd "${target_dir}" || log_error "Failed to enter '${target_dir}'."
        return 0
    fi

    log_info "Executing: ${GIT_CMD} clone -b ${REMOTE_BRANCH} ${REPO_URL} ${target_dir}"
    "${GIT_CMD}" clone -b "${REMOTE_BRANCH}" "${REPO_URL}" "${target_dir}"
    
    cd "${target_dir}" || log_error "Failed to enter '${target_dir}'."
    log_info "CLONE Operation completed successfully."
    return 0
}

# ----------------------------------------------------------------------
# --- Main Execution Flow ---
# ----------------------------------------------------------------------

# 4. Check for required SYNC_METHOD and proceed with initialization
if [ -z "${SYNC_METHOD}" ]; then
    log_error "Missing required argument --sync-method."
fi

if [ "${SYNC_METHOD}" == "init-and-sync" ]; then
    if [ -z "${REPO_URL}" ]; then
        log_error "REPO_URL is required for init-and-sync. Set the GIT_REPO_URL variable or use --repo-url."
    fi
    # Execute clone and subsequent operations in a subshell to isolate directory changes
    (clone_operation && PULL_METHOD="${PULL_METHOD:-fetch-merge}" && SYNC_METHOD="pull-only")
    # If clone_operation or subsequent commands in subshell fail, the script will exit due to set -e
fi

# 5. Validation checks
if ! "${GIT_CMD}" rev-parse --is-inside-work-tree > /dev/null 2>&1 && [ "${DRY_RUN}" -eq 0 ]; then
    log_error "Not inside a Git working directory. Use --sync-method=init-and-sync if necessary."
fi

if [ -z "${LOCAL_BRANCH}" ]; then
    LOCAL_BRANCH="$("${GIT_CMD}" rev-parse --abbrev-ref HEAD)"
    # If rev-parse fails, it means we are not in a git repo or HEAD is detached.
    # With set -e, this would exit. We need to handle it gracefully for dry-run.
    if [ "$?" -ne 0 ] && [ "${DRY_RUN}" -eq 0 ]; then
        log_error "Could not determine the current local branch. Are you in a Git repository?"
    fi
fi

if ! set_upstream_config; then exit 1; fi

if ( [ "${SYNC_METHOD}" == "pull-only" ] || [ "${SYNC_METHOD}" == "pull-push" ] ) && [ -z "${PULL_METHOD}" ]; then
    log_error "--pull-method is required for '${SYNC_METHOD}'."
fi
if ( [ "${SYNC_METHOD}" == "push-only" ] || [ "${SYNC_METHOD}" == "pull-push" ] ) && [ -z "${PUSH_METHOD}" ]; then
    log_error "--push-method is required for '${SYNC_METHOD}'."
fi

log_info "SYNC: Synchronization starting..."
log_info "Configuration: Local Branch=${LOCAL_BRANCH}, Remote=${REMOTE_NAME}/${REMOTE_BRANCH}"
log_info "Mode: ${SYNC_METHOD}"
log_info "Options: DryRun=${DRY_RUN}, Prune=${PRUNE}, UseUpstream=${USE_UPSTREAM}, FFOnly=${FF_ONLY}, AtomicPush=${ATOMIC_PUSH}, PullStrategy=${PULL_STRATEGY}"
log_info "---------------------------------------------------"

# 6. Execute based on SYNC_METHOD
case "${SYNC_METHOD}" in
    pull-only) pull_operation "${PULL_METHOD}" ;;
    push-only) push_operation "${PUSH_METHOD}" ;;
    pull-push)
        pull_operation "${PULL_METHOD}"
        log_info "Pull completed. Proceeding with Push."
        push_operation "${PUSH_METHOD}"
        ;;
    *) log_error "Invalid sync method provided.";;
esac

log_info "---------------------------------------------------"
log_info "Synchronization process finished."