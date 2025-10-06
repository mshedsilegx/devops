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
    - **Locking**: To prevent race conditions, the script uses an atomic, repository-specific locking mechanism. It creates a lock directory in a temporary directory (e.g., `/tmp`) with a unique name derived from the repository's path (e.g., `/tmp/git_sync_<repo_hash>.lockdir`). This ensures that synchronization operations for the same repository do not run concurrently, while allowing different repositories to be synced in parallel. The lock is automatically released on script exit, error, or interruption.
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
| `--sync-method=<method>`       | The primary action to perform: `pull-only`, `push-only`, `pull-and-push`, `clone-and-pull`, `init-and-push`. | `string`  | (none)                                |
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
./git_sync.sh --sync-method=pull-and-push --pull-method=fetch-merge --push-method=default --remote-branch=main
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

### Clone a Repository and Pull

Clone a new repository if it doesn't exist locally, and then pull the latest changes using a rebase strategy.

```bash
./git_sync.sh \
  --sync-method=clone-and-pull \
  --repo-url=git@github.com:my-user/my-repo.git \
  --pull-method=fetch-rebase

### Initialize a Local Repository and Push

Initialize a git repository in the current directory (if it's not one already), add all files, and push them to a new, empty remote repository.

```bash
./git_sync.sh \
  --sync-method=init-and-push \
  --repo-url=git@github.com:my-user/new-repo.git \
  --remote-branch=main
```
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

## 5. In-Depth Option Explanations

### Synchronization Methods (`--sync-method`)
-   **`pull-only`**: Fetches changes from the remote repository and applies them to the local branch. This is useful for updating a local workspace without pushing any local changes.
-   **`push-only`**: Pushes local commits to the remote repository. This is useful when you have committed changes locally and want to share them.
-   **`pull-and-push`**: The most common workflow. It first pulls changes from the remote to ensure the local branch is up-to-date, then pushes local commits.
-   **`clone-and-pull`**: Designed for initial setup. It clones the repository if it doesn't already exist in the specified directory, and then performs a pull operation to ensure it's synchronized.
-   **`init-and-push`**: Initializes a Git repository in the current directory if one does not already exist, adds all files, creates an initial commit, and pushes them to a new or empty remote repository. This is ideal for turning a local project into a new remote repository.

### Pull Methods (`--pull-method`)
-   **`pull`**: Executes a standard `git pull` command, which is a shorthand for fetching and then merging or rebasing (depending on `--pull-strategy`).
-   **`fetch-merge`**: A more explicit two-step process. It first runs `git fetch` to retrieve all new data from the remote, then runs `git merge` to integrate the changes. This creates a merge commit if the histories have diverged.
-   **`fetch-rebase`**: Fetches from the remote and then uses `git rebase` to re-apply local commits on top of the updated remote branch. This results in a linear history but rewrites commit hashes.
-   **`fetch-reset`**: A **destructive** operation that makes the local branch exactly match the remote branch. It fetches the latest data and then runs `git reset --hard`. Any local commits that have not been pushed will be permanently lost. Requires `--force-dangerous-operations`.

### Push Methods (`--push-method`)
-   **`default`**: Performs a standard `git push`. This will fail if the push is not a fast-forward (i.e., if the remote has changes you don't have locally).
-   **`force`**: Performs a `git push --force-with-lease`. This is a **destructive** operation that overwrites the remote branch with the local one. It's safer than `--force` because it will not overwrite work if someone else has pushed to the remote branch since you last pulled. Requires `--force-dangerous-operations`.
-   **`set-upstream`**: Pushes the current branch and adds the upstream (tracking) reference. This is useful the first time you push a new branch (`git push -u origin <branch>`).

### Other Important Options
-   **`--pull-strategy=<strategy>`**: Only used with `--pull-method=pull`. It specifies whether to use a `merge` (creates a merge commit) or `rebase` (linear history) strategy when pulling.
-   **`--prune`**: When fetching, this option removes any remote-tracking references that no longer exist on the remote. It helps keep your local repository clean.
-   **`--ff-only`**: When merging (with `pull` or `fetch-merge`), this ensures that the merge is only completed if it's a fast-forward. If the branches have diverged, the merge will fail.
-   **`--atomic-push`**: Ensures that when pushing multiple branches, either all of them are updated on the remote, or none are. This prevents the remote repository from ending up in a partially updated state.