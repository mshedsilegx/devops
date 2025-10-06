#!/bin/bash

# ======================================================================
# Git Synchronization Script (v0.0.9xg - 2025/10/04)
#
# A comprehensive script for automating Git synchronization. This final
# version includes a full feature set, robust error handling, security
# hardening, and detailed documentation.
# ======================================================================

# --- Script Setup ---
set -euo pipefail

# --- Global Variables ---
REPO_URL=""
REMOTE_NAME="origin"
REMOTE_BRANCH="main"
LOCAL_BRANCH=""
LOCAL_DIR=""
PULL_STRATEGY="merge"
CUSTOM_COMMIT_MESSAGE="Automated commit"

SYNC_METHOD=""
PULL_METHOD=""
PUSH_METHOD=""
DRY_RUN=0
PRUNE=0
USE_UPSTREAM=0
FF_ONLY=0
ATOMIC_PUSH=0
FORCE_DANGEROUS=0
GIT_CMD="git"
# Directory based lock is dynamically generated per repository

# --- Logging Functions ---
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

# --- Lock Functions ---
get_temp_dir() {
    # Use TMP if set, otherwise default to /tmp
    local temp_dir="${TMP:-/tmp}"
    # Ensure the directory exists and is writable
    if [ ! -d "${temp_dir}" ] || [ ! -w "${temp_dir}" ]; then
        log_error "The temporary directory '${temp_dir}' is not a writable directory. Please set TMP to a valid path."
    fi
    echo "${temp_dir}"
}

get_lock_dir_path() {
    # Get the top-level directory of the repository to create a unique identifier
    local repo_path
    repo_path=$(git rev-parse --show-toplevel)

    # Create a unique but consistent hash based on the repository path
    local repo_identifier
    repo_identifier=$(echo -n "${repo_path}" | md5sum | cut -d' ' -f1)

    local temp_dir
    temp_dir=$(get_temp_dir)

    echo "${temp_dir}/git_sync_${repo_identifier}.lockdir"
}

acquire_lock() {
    local lock_dir_path="$1"
    # Atomically create the lock directory. Fails if it already exists.
    if ! mkdir "${lock_dir_path}" 2>/dev/null; then
        return 1
    fi
    log_info "Lock acquired at ${lock_dir_path}."
    return 0
}

release_lock() {
    local lock_dir_path="$1"
    if [ -d "${lock_dir_path}" ]; then
        rmdir "${lock_dir_path}"
        log_info "Lock directory removed from ${lock_dir_path}."
    fi
}

# --- Security and State Check Functions ---
sanitize_input() {
    # Basic sanitization to prevent command injection in merge messages
    echo "$1" | tr -d ';&|()`<>*$'
}

confirm_dangerous_operation() {
    local operation_name=$1
    if [ "${FORCE_DANGEROUS}" -ne 1 ]; then
        log_error "The operation '${operation_name}' is potentially destructive and can lead to data loss. To proceed, you must add the '--force-dangerous-operations' flag. This is a safety measure to prevent accidents."
    fi
    log_warn "Proceeding with dangerous operation '${operation_name}'. Ensure you have a backup if necessary."
}

check_repo_state() {
    if [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ]; then
        log_error "A rebase is currently in progress. Please resolve or abort it before running this script."
    fi
    if [ -f ".git/MERGE_HEAD" ]; then
        log_error "A merge is currently in progress. Please resolve or abort it before running this script."
    fi
    log_info "Repository state is clean."
}

# --- Usage Information ---
usage() {
    cat <<EOF >&2
Usage: $0 --sync-method=<method> [options...]

Description:
  A powerful script to automate Git synchronization. It supports various pull and push
  strategies, handles repository initialization, and includes safety features to
  prevent common issues like race conditions and accidental data loss.

  For secure authentication, it is highly recommended to use a Git credential helper
  (https://git-scm.com/docs/git-credential-helpers) instead of embedding credentials
  in the repository URL.

Primary Synchronization Methods:
  --sync-method=<method>    : The main action to perform.
    - pull-only             : Only pull changes from the remote.
    - push-only             : Only push changes to the remote.
    - pull-and-push         : Pull changes, then push.
    - clone-and-pull        : Clone the repo if it doesn't exist, then perform a pull.
    - init-and-push         : Initialize a new local repo and push it to an empty remote.

Pull Options:
  --pull-method=<method>    : The strategy for pulling changes.
    - pull                  : Use 'git pull' with a specified strategy.
    - fetch-merge           : Fetch and then merge.
    - fetch-rebase          : Fetch and then rebase.
    - fetch-reset           : DANGEROUS: Fetch and hard reset to the remote branch.
  --pull-strategy=<strategy>: 'merge' or 'rebase' (for --pull-method=pull). Default: merge.
  --ff-only                 : Allow merge only if it can be a fast-forward.

Push Options:
  --push-method=<method>    : The strategy for pushing changes.
    - default               : Use 'git push'.
    - force                 : DANGEROUS: Use 'git push --force-with-lease'.
    - set-upstream          : Use 'git push -u' to set the upstream tracking branch.
  --atomic-push             : Push all refs atomically.

General Options:
  --custom-commit-message=<msg>: A custom message for any commit made by the script (merge, initial, etc.).
  --repo-url=<url>          : The URL of the Git repository.
  --remote-name=<name>      : The name of the remote (default: origin).
  --remote-branch=<branch>  : The remote branch to sync with (default: main).
  --local-dir=<path>        : The local directory to clone into.
  --use-upstream            : Automatically use the branch's tracking information.
  --prune                   : Prune stale remote-tracking branches during fetch/pull.
  --dry-run                 : Print the git commands that would be executed without running them.
  --force-dangerous-operations: A required flag to execute 'force' push or 'fetch-reset'.
  -h, --help                : Display this help message.
EOF
    exit 1
}

# --- Core Functions ---
load_env_config() {
    local env_file="git_sync.env"
    if [ -f "${env_file}" ]; then
        log_info "Sourcing configuration from ${env_file}"
        set -a
        # shellcheck source=/dev/null
        . "${env_file}"
        set +a
    fi
    REPO_URL="${GIT_REPO_URL:-${REPO_URL}}"
    REMOTE_NAME="${GIT_REMOTE_NAME:-${REMOTE_NAME}}"
    REMOTE_BRANCH="${GIT_REMOTE_BRANCH:-${REMOTE_BRANCH}}"
    LOCAL_BRANCH="${GIT_LOCAL_BRANCH:-${LOCAL_BRANCH}}"
    LOCAL_DIR="${GIT_LOCAL_DIR:-${LOCAL_DIR}}"
    PULL_STRATEGY="${GIT_PULL_STRATEGY:-${PULL_STRATEGY}}"
}

parse_args() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --sync-method=*) SYNC_METHOD="${1#*=}"; shift 1 ;;
            --pull-method=*) PULL_METHOD="${1#*=}"; shift 1 ;;
            --push-method=*) PUSH_METHOD="${1#*=}"; shift 1 ;;
            --pull-strategy=*) PULL_STRATEGY="${1#*=}"; shift 1 ;;
            --custom-commit-message=*) CUSTOM_COMMIT_MESSAGE=$(sanitize_input "${1#*=}"); shift 1 ;;
            --repo-url=*) REPO_URL="${1#*=}"; shift 1 ;;
            --remote-name=*) REMOTE_NAME="${1#*=}"; shift 1 ;;
            --remote-branch=*) REMOTE_BRANCH="${1#*=}"; shift 1 ;;
            --local-dir=*) LOCAL_DIR="${1#*=}"; shift 1 ;;
            --dry-run) DRY_RUN=1; shift 1 ;;
            --prune) PRUNE=1; shift 1 ;;
            --use-upstream) USE_UPSTREAM=1; shift 1 ;;
            --ff-only) FF_ONLY=1; shift 1 ;;
            --atomic-push) ATOMIC_PUSH=1; shift 1 ;;
            --force-dangerous-operations) FORCE_DANGEROUS=1; shift 1 ;;
            -h|--help) usage ;;
            *) log_error "Unknown option: $1. Use -h or --help for usage information.";;
        esac
    done
}

set_upstream_config() {
    if [ "${USE_UPSTREAM}" -eq 1 ]; then
        log_info "Using --use-upstream to determine tracking branch..."
        local upstream_ref
        upstream_ref=$(${GIT_CMD} rev-parse --symbolic-full-name --abbrev-ref "@{u}" 2>/dev/null || echo "")
        if [ -z "${upstream_ref}" ]; then
            log_error "The current branch is not tracking a remote branch. Cannot use --use-upstream."
        fi
        REMOTE_NAME=$(echo "${upstream_ref}" | cut -d/ -f1)
        REMOTE_BRANCH=$(echo "${upstream_ref}" | cut -d/ -f2-)
        log_info "Dynamically set tracking to: ${REMOTE_NAME}/${REMOTE_BRANCH}"
    fi
}

# --- Git Operations ---
clone_operation() {
    log_info "--- CLONE Operation ---"
    local target_dir="${LOCAL_DIR:-$(basename "${REPO_URL}" .git)}"
    if [ -d "${target_dir}/.git" ]; then
        log_info "Git repository already exists in '${target_dir}'. Skipping clone."
        cd "${target_dir}" || log_error "Failed to enter directory '${target_dir}'."
        return
    fi
    log_info "Cloning '${REPO_URL}' into '${target_dir}'"
    "${GIT_CMD}" clone --branch "${REMOTE_BRANCH}" -- "${REPO_URL}" "${target_dir}"
    cd "${target_dir}" || log_error "Failed to enter directory '${target_dir}'."
}

init_and_push_operation() {
    log_info "--- INIT & PUSH Operation ---"

    if [ -z "${REPO_URL}" ]; then
        log_error "REPO_URL is required for init-and-push. Set it in git_sync.env or use --repo-url."
    fi

    if [ ! -d ".git" ]; then
        log_info "Initializing a new Git repository..."
        "${GIT_CMD}" init
    else
        log_warn "This directory is already a Git repository."
    fi

    # Check for local branch, default to main if not set
    if [ -z "${LOCAL_BRANCH}" ]; then
        # Check current branch, if not exists, checkout to a new one
        if ! git symbolic-ref -q HEAD >/dev/null; then
             log_info "No branch found, creating branch '${REMOTE_BRANCH}'."
             "${GIT_CMD}" checkout -b "${REMOTE_BRANCH}"
        fi
        LOCAL_BRANCH=$("${GIT_CMD}" rev-parse --abbrev-ref HEAD)
    fi

    if ! ("${GIT_CMD}" remote | grep -q "^${REMOTE_NAME}$"); then
        log_info "Adding remote '${REMOTE_NAME}' with URL '${REPO_URL}'"
        "${GIT_CMD}" remote add "${REMOTE_NAME}" "${REPO_URL}"
    else
        log_info "Remote '${REMOTE_NAME}' already exists. Ensuring URL is correct."
        "${GIT_CMD}" remote set-url "${REMOTE_NAME}" "${REPO_URL}"
    fi

    log_info "Staging all files..."
    "${GIT_CMD}" add .

    if ! "${GIT_CMD}" diff --staged --quiet; then
        log_info "Creating commit with message: '${CUSTOM_COMMIT_MESSAGE}'"
        "${GIT_CMD}" commit -m "${CUSTOM_COMMIT_MESSAGE}"
    else
        log_info "No changes to commit. If this is a new repository, it might be empty."
    fi

    if ! git rev-parse --quiet --verify HEAD >/dev/null; then
        log_warn "No commits found. Nothing to push."
        return
    fi

    log_info "Pushing local branch '${LOCAL_BRANCH}' to remote '${REMOTE_NAME}/${REMOTE_BRANCH}'..."
    "${GIT_CMD}" push --set-upstream "${REMOTE_NAME}" "${LOCAL_BRANCH}:${REMOTE_BRANCH}"

    log_info "INIT & PUSH operation completed."
}

pull_operation() {
    log_info "--- PULL Operation (Method: ${PULL_METHOD}) ---"
    check_repo_state
    local prune_flag=""
    [ "${PRUNE}" -eq 1 ] && prune_flag="--prune"
    local merge_options=""
    [ "${FF_ONLY}" -eq 1 ] && merge_options="--ff-only"

    case "${PULL_METHOD}" in
        pull)
            "${GIT_CMD}" pull ${prune_flag} ${merge_options} --${PULL_STRATEGY} -- "${REMOTE_NAME}" "${REMOTE_BRANCH}:${LOCAL_BRANCH}"
            ;;
        fetch-merge)
            "${GIT_CMD}" fetch ${prune_flag} -- "${REMOTE_NAME}" "${REMOTE_BRANCH}"
            if ! "${GIT_CMD}" merge ${merge_options} --no-edit -m "${CUSTOM_COMMIT_MESSAGE}" -- "${REMOTE_NAME}/${REMOTE_BRANCH}"; then
                "${GIT_CMD}" merge --abort || log_warn "git merge --abort failed. The repository may be in a conflicted state."
                log_error "Merge conflict occurred. Please resolve it manually."
            fi
            ;;
        fetch-rebase)
            "${GIT_CMD}" fetch ${prune_flag} -- "${REMOTE_NAME}" "${REMOTE_BRANCH}"
            if ! "${GIT_CMD}" rebase -- "${REMOTE_NAME}/${REMOTE_BRANCH}"; then
                "${GIT_CMD}" rebase --abort || log_warn "git rebase --abort failed. The repository may be in a conflicted state."
                log_error "Rebase conflict occurred. Please resolve it manually."
            fi
            ;;
        fetch-reset)
            confirm_dangerous_operation "fetch-reset"
            "${GIT_CMD}" fetch ${prune_flag} -- "${REMOTE_NAME}" "${REMOTE_BRANCH}"
            "${GIT_CMD}" reset --hard -- "${REMOTE_NAME}/${REMOTE_BRANCH}"
            ;;
        *) log_error "Invalid pull method: '${PULL_METHOD}'.";;
    esac
    log_info "PULL operation completed."
}

push_operation() {
    log_info "--- PUSH Operation (Method: ${PUSH_METHOD}) ---"
    check_repo_state
    local atomic_flag=""
    [ "${ATOMIC_PUSH}" -eq 1 ] && atomic_flag="--atomic"
    local push_options=""

    case "${PUSH_METHOD}" in
        default) push_options="";;
        force)
            confirm_dangerous_operation "force push"
            push_options="--force-with-lease"
            ;;
        set-upstream) push_options="-u";;
        *) log_error "Invalid push method: '${PUSH_METHOD}'.";;
    esac
    "${GIT_CMD}" push ${atomic_flag} ${push_options} -- "${REMOTE_NAME}" "${LOCAL_BRANCH}:${REMOTE_BRANCH}"
    log_info "PUSH operation completed."
}

# --- Main Execution ---
main() {
    load_env_config
    parse_args "$@"

    if [ "${DRY_RUN}" -eq 1 ]; then
        GIT_CMD="echo git"
        log_warn "DRY RUN MODE ENABLED: Commands will be printed but not executed."
    fi

    if [ -z "${SYNC_METHOD}" ]; then
        log_error "Missing required argument --sync-method. Use --help for more information."
    fi

    # Check for embedded credentials in the URL and warn the user
    if [[ "${REPO_URL}" == *"://"*@"*"* ]]; then
        log_warn "The repository URL appears to contain embedded credentials. For better security, please use a Git credential helper instead."
    fi

    if [ "${SYNC_METHOD}" == "clone-and-pull" ]; then
        if [ -z "${REPO_URL}" ]; then
            log_error "REPO_URL is required for clone-and-pull. Set it in git_sync.env or use --repo-url."
        fi
        clone_operation
    fi

    # From this point, we expect to be inside a Git repository for most operations.
    if [ "${SYNC_METHOD}" != "init-and-push" ] && ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        log_error "Not inside a Git repository. For initial cloning, use --sync-method=clone-and-pull or for creating a new one use --sync-method=init-and-push."
    fi

    # --- LOCKING & STATE CHECK ---
    if [ "${DRY_RUN}" -eq 0 ]; then
        local lock_dir
        if [ "${SYNC_METHOD}" == "init-and-push" ]; then
            # In init-and-push, the .git dir might not exist, so we can't rely on git rev-parse
            # We will create a lock based on the current directory path
            local lock_base_path
            lock_base_path=$(pwd)
            local repo_identifier
            repo_identifier=$(echo -n "${lock_base_path}" | md5sum | cut -d' ' -f1)
            local temp_dir
            temp_dir=$(get_temp_dir)
            lock_dir="${temp_dir}/git_sync_${repo_identifier}.lockdir"
        else
            lock_dir=$(get_lock_dir_path)
        fi

        # Attempt to acquire the lock. If it fails, another instance is running.
        if ! acquire_lock "${lock_dir}"; then
            log_error "Failed to acquire lock. Another instance may be running. Lock directory: ${lock_dir}"
        fi

        # If the script exits for any reason from this point on, the trap will release the lock.
        trap 'release_lock "${lock_dir}"' EXIT SIGINT SIGTERM

        if [ "${SYNC_METHOD}" != "init-and-push" ]; then
            check_repo_state
        fi
    fi

    if [ -z "${LOCAL_BRANCH}" ]; then
        if git symbolic-ref -q HEAD >/dev/null 2>&1; then
            LOCAL_BRANCH=$(${GIT_CMD} rev-parse --abbrev-ref HEAD)
        elif [ "${SYNC_METHOD}" != "init-and-push" ]; then
            log_warn "Detached HEAD state detected. Operations will be limited and push is disabled."
            LOCAL_BRANCH=$(${GIT_CMD} rev-parse HEAD) # Get commit hash for context
            if [[ "${SYNC_METHOD}" =~ "push" ]]; then
                log_error "Push operations are disabled in a detached HEAD state."
            fi
        fi
    fi

    if [ "${SYNC_METHOD}" != "init-and-push" ]; then
        set_upstream_config
    fi

    if [[ "${SYNC_METHOD}" =~ "pull" ]] && [ -z "${PULL_METHOD}" ]; then
        log_error "--pull-method is required for sync method '${SYNC_METHOD}'."
    fi
    if [[ "${SYNC_METHOD}" =~ "push" ]] && [ -z "${PUSH_METHOD}" ] && [ "${SYNC_METHOD}" != "init-and-push" ]; then
        log_error "--push-method is required for sync method '${SYNC_METHOD}'."
    fi

    log_info "SYNC Starting: ${SYNC_METHOD}"
    if [ "${SYNC_METHOD}" != "init-and-push" ]; then
        log_info "Configuration: Local Branch='${LOCAL_BRANCH}', Remote='${REMOTE_NAME}/${REMOTE_BRANCH}'"
    fi

    case "${SYNC_METHOD}" in
        pull-only)
            pull_operation || log_error "The pull operation failed. Please check the output above for details."
            ;;
        push-only)
            push_operation || log_error "The push operation failed. Please check the output above for details."
            ;;
        pull-and-push)
            pull_operation || log_error "The pull operation failed. Please check the output above for details."
            log_info "Pull complete, proceeding with push."
            push_operation || log_error "The push operation failed. Please check the output above for details."
            ;;
        clone-and-pull)
            if [ -n "${PULL_METHOD}" ]; then
                log_info "Initial clone/setup complete, proceeding with configured pull method."
                pull_operation || log_error "The pull operation failed. Please check the output above for details."
            else
                log_info "Initial clone/setup complete. No pull method specified, so no further action will be taken."
            fi
            ;;
        init-and-push)
            init_and_push_operation || log_error "The init-and-push operation failed. Please check the output above."
            ;;
        *) log_error "Invalid sync method '${SYNC_METHOD}'.";;
    esac

    log_info "Synchronization process finished successfully."
    exit 0
}

if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi
