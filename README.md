# Git Sync Script

## 1. Application Overview and Objectives

`git_sync.sh` is a powerful and robust Bash script designed to automate Git synchronization tasks. It provides a flexible command-line interface to handle a wide range of version control workflows, from simple pulls and pushes to complex repository initialization and history manipulation.

The primary objectives of this script are:
- **Automation**: Simplify and automate common Git operations to improve development and deployment workflows.
- **Robustness**: Provide strong error handling and state checking to ensure that operations are performed safely and predictably.
- **Security**: Implement safety features to prevent accidental data loss and mitigate potential security risks.
- **Flexibility**: Offer a rich set of options to support various synchronization strategies, such as merging, rebasing, and force pushing with safeguards.

## 2. Architecture and Design Choices

The script is designed with modularity, security, and maintainability in mind.

- **Modular Design**: The script is broken down into logical, single-purpose functions (e.g., `load_env_config`, `parse_args`, `acquire_lock`, `check_repo_state`, `pull_operation`). This makes the code easier to read, debug, and extend. The main execution logic is encapsulated in a `main` function.

- **Configuration Hierarchy**: Configuration is loaded in a hierarchical manner, providing maximum flexibility:
    1.  **Command-Line Arguments**: Highest priority. Any option passed directly to the script will override other settings.
    2.  **Environment Variables**: Can be used to set configuration for a specific shell session.
    3.  **`git_sync.env` File**: Lowest priority. Provides default settings for a given environment.

- **Security and Safety**:
    - **Locking**: A file-based lock (`/tmp/git_sync.lock`) is used to prevent race conditions by ensuring only one instance of the script runs at a time. The lock is automatically released on script exit, error, or interruption.
    - **Input Sanitization**: User-provided strings, such as the merge commit message, are sanitized to remove characters that could be used for command injection.
    - **Dangerous Operation Confirmation**: Potentially destructive operations like `fetch-reset` and `force` push require an explicit `--force-dangerous-operations` flag to prevent accidental data loss.

- **Error Handling**:
    - The script uses `set -euo pipefail` to exit immediately if any command fails, ensuring that errors do not go unnoticed.
    - Before performing any Git operations, the script checks if the repository is in a clean state (i.e., no ongoing merge or rebase).
    - It gracefully handles detached HEAD states by detecting them and disabling operations that are not safe to perform.

## 3. Command-Line Arguments

The script's behavior is controlled through a series of command-line arguments.

| Argument                       | Description                                                                                             | Type      | Default                               |
| ------------------------------ | ------------------------------------------------------------------------------------------------------- | --------- | ------------------------------------- |
| `--sync-method=<method>`       | The primary action to perform: `pull-only`, `push-only`, `pull-push`, `init-and-sync`.                   | `string`  | (none)                                |
| `--pull-method=<method>`       | The strategy for pulling: `pull`, `fetch-merge`, `fetch-rebase`, `fetch-reset`.                         | `string`  | (none)                                |
| `--push-method=<method>`       | The strategy for pushing: `default`, `force`, `set-upstream`.                                           | `string`  | (none)                                |
| `--pull-strategy=<strategy>`   | The strategy for the `pull` method: `merge` or `rebase`.                                                | `string`  | `merge`                               |
| `--merge-commit-message=<msg>` | A custom message for the merge commit (will be sanitized).                                              | `string`  | `Automated merge by git_sync.sh`      |
| `--repo-url=<url>`             | The URL of the Git repository (required for `init-and-sync`).                                           | `string`  | (from `git_sync.env`)                 |
| `--remote-name=<name>`         | The name of the remote to sync with.                                                                    | `string`  | `origin`                              |
| `--remote-branch=<branch>`     | The remote branch to sync with.                                                                         | `string`  | `main`                                |
| `--local-dir=<path>`           | The local directory to clone into.                                                                      | `string`  | (repo name from URL)                  |
| `--use-upstream`               | Automatically use the branch's tracking information for remote name and branch.                         | `flag`    | (disabled)                            |
| `--prune`                      | Prune stale remote-tracking branches during fetch or pull.                                              | `flag`    | (disabled)                            |
| `--ff-only`                    | Allow a merge only if it can be resolved as a fast-forward.                                             | `flag`    | (disabled)                            |
| `--atomic-push`                | Push all refs atomically.                                                                               | `flag`    | (disabled)                            |
| `--dry-run`                    | Print the git commands that would be executed without running them.                                     | `flag`    | (disabled)                            |
| `--force-dangerous-operations` | A required safety flag to execute `force` push or `fetch-reset`.                                        | `flag`    | (disabled)                            |
| `-h`, `--help`                 | Display the help message.                                                                               | `flag`    | (disabled)                            |

## 4. Examples

### Basic Pull and Push

Perform a standard pull (fetch and merge) and then push to the `main` branch on `origin`.

```bash
./git_sync.sh --sync-method=pull-push --pull-method=fetch-merge --push-method=default --remote-branch=main
```

### Perform a Pull Only

Update the current branch with the latest changes from the remote using a rebase strategy.

```bash
./git_sync.sh --sync-method=pull-only --pull-method=fetch-rebase
```

### Perform a Push Only

Push local commits to the remote `main` branch.

```bash
./git_sync.sh --sync-method=push-only --push-method=default --remote-branch=main
```

### Initialize a Repository and Sync

Clone a new repository if it doesn't exist locally, and then pull the latest changes using a rebase strategy.

```bash
./git_sync.sh \
  --sync-method=init-and-sync \
  --repo-url=git@github.com:my-user/my-repo.git \
  --pull-method=fetch-rebase
```

### Reset a Local Branch to Match the Remote (Dangerous)

Force the local `feature` branch to match the remote `feature` branch exactly, discarding any local changes. This requires the `--force-dangerous-operations` flag.

```bash
./git_sync.sh \
  --sync-method=pull-only \
  --pull-method=fetch-reset \
  --remote-branch=feature \
  --force-dangerous-operations
```

### Using the `git_sync.env` Configuration File

You can set default configurations in a `git_sync.env` file in the same directory as the script.

**`git_sync.env`:**
```
GIT_REPO_URL="git@github.com:my-user/my-repo.git"
GIT_REMOTE_NAME="origin"
GIT_REMOTE_BRANCH="develop"
```

Now you can run the script with fewer arguments:
```bash
# Clones the repo from the URL in the .env file and pulls from the 'develop' branch
./git_sync.sh --sync-method=init-and-sync --pull-method=fetch-merge
```