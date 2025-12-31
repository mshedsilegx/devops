# Git Autosync Utility

## Application Overview and Objectives
`git_autosync.sh` is a robust Bash utility designed to automate the synchronization of multiple Git repositories within a specified directory tree. Its primary objective is to streamline the development workflow by automatically staging, committing, and syncing local changes with remote repositories.

The script is particularly useful for developers managing numerous microservices, documentation repos, or configuration projects, ensuring that no work is left uncommitted and that local copies stay up-to-date with minimal manual intervention.

## Prerequisites
*   **Git**: Version 2.0 or higher recommended.
*   **Bash**: Version 4.0 or higher.
*   **Environment**: Linux, macOS, WSL, or Git Bash (Windows).

## Recommended Global Git Configuration
For the most seamless automated workflow, the following global configurations are recommended:

| Command | Rationale |
| :--- | :--- |
| `git config --global pull.rebase true` | Makes rebase the default for every pull, ensuring linear history. |
| `git config --global rebase.autoStash true` | Automatically stashes and reapplies local changes during rebase. |
| `git config --global fetch.prune true` | Automatically removes local "ghost" branches that no longer exist on the server. |

## Architecture and Design Choices
The script is built with several key architectural principles in mind:

1.  **Decoupled Synchronization**: Stage 1 (Local) and Stage 2 (Network) are decoupled. The script ensures that even if no new local changes are detected, it still pulls remote updates and pushes any existing local commits.
2.  **Ordered Synchronization**: Even when running in parallel, the script ensures that output is re-assembled and displayed in the original order they were discovered. This prevents interleaved output and makes logs readable.
3.  **Dynamic Concurrency**: Automatically detects the number of available CPU cores (`nproc` on Linux, `sysctl` on macOS, `%NUMBER_OF_PROCESSORS%` on Windows) to optimize parallel defaults.
4.  **Sequential Safety**: While repositories are processed in parallel, the results are aggregated and reported sequentially to ensure atomic logs for each project.
5.  **Safety First**: Includes checks for detached HEAD states, missing remotes, and directory access permissions. It automatically aborts failed rebases to keep repositories in a clean state.
6.  **Signal Handling**: Implements a robust `trap` mechanism for `EXIT`, `SIGINT`, and `SIGTERM` to ensure that orphaned background processes are terminated and temporary status files are purged.
7.  **Automation Friendly**: Configures Git and SSH for non-interactive mode (`BatchMode`), preventing the script from hanging on authentication prompts.
8.  **Portability**: Relies on standard Bash and Git commands, making it compatible with Linux, macOS, WSL, and Git Bash.
9.  **Information Density**: Employs `-print0` and `git status --porcelain` to handle complex file paths and provide stable detection logic.
10. **Progress Transparency**: Provides a real-time progress indicator (`Processing repositories...`) in both sequential and parallel modes when verbose output is enabled.
11. **Quiet by Default**: Optimizes for core information. Unless `--verbose` is enabled, the script only reports repositories where actions were taken (commits made, updates pulled, or changes pushed), errors occurred, or changes were detected in dry-run mode. Each status message includes the current short Git hash at the end of the line in angle brackets (e.g., `<a1b2c3d>`) for easy reference.
12. **Clear Network Status**: In verbose mode, the script explicitly labels `Pull:` and `Push:` operations to distinguish between remote updates and local uploads.

## Command Line Arguments

| Argument | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--base-folder=<path>` | **Mandatory.** The root directory to search for Git repositories. | String | N/A |
| `--detect-only` | Reports changes without performing any commits, pulls, or pushes. | Flag | `false` |
| `--message="<msg>"` | Custom commit message for auto-generated commits. | String | `Auto-sync: YYYY-MM-DD HH:MM:SS` |
| `--verbose` | Enables detailed output, including progress separators for each project. | Flag | `false` |
| `--parallel[=N,T]` | Enables parallel execution. `N` is the number of concurrent processes, `T` is an optional delay in seconds. | String | `1,0` (or `NPROC` if flag is standalone) |
| `--logfile=<path>` | Path to a file where all console output will be permanently saved. | String | N/A |
| `--help` | Displays the usage instructions and exits. | Flag | N/A |

## Examples

### Basic Usage
Sync all repositories under the `projects` folder:
```bash
./git_autosync.sh --base-folder=~/projects
```

### Dry Run
Check which repositories have changes without modifying them:
```bash
./git_autosync.sh --base-folder=~/projects --detect-only
```

### Parallel Execution (Optimal)
Sync using all available CPU cores:
```bash
./git_autosync.sh --base-folder=~/projects --parallel
```

### Custom Commit Message with Concurrent Processing
```bash
./git_autosync.sh --base-folder=~/projects --message="Workstation backup" --parallel=4,1 --verbose
```

### Full Synchronization with Logging
Sync all repositories and save the entire session output to a log file:
```bash
./git_autosync.sh --base-folder=~/projects --logfile=~/logs/sync_$(date +%Y%m%d).log
```

## Git Strategy and Commands

The script follows a **Decoupled Sync Strategy**:
1.  **Local Stage**: Uses `git status --porcelain` to detect uncommitted changes. If found, it creates a commit using the specified message.
2.  **Network Stage**: Always attempts a `git pull --rebase` followed by a `git push`. This ensures that:
    *   Remote changes are integrated even if the local working tree is clean.
    *   Manually created local commits (or commits from previous partial syncs) are pushed to the server.

In `--detect-only` mode, the script performs a passive check, reporting on both working tree changes and whether the local branch is ahead or behind its remote counterpart.

### Command Reference

| Command | Purpose in Script |
| :--- | :--- |
| `git status --porcelain` | Detects local changes in a stable, machine-readable format. |
| `git status -uno` | Checks ahead/behind status relative to remote in detect-only mode. |
| `git add -A` | Stages all changes (including deletions and new files). |
| `git commit -m "<msg>"` | Creates a local commit with a timestamp or custom message. |
| `git rev-parse HEAD` | Captures the full repository hash before and after sync to detect changes reliably. |
| `git rev-parse --short HEAD` | Retrieves the short hash for display in status messages. |
| `git rev-parse --abbrev-ref HEAD` | Retrieves the current branch name. |
| `git rev-parse --abbrev-ref --symbolic-full-name @{u}` | Checks if the current branch has an upstream tracking branch configured. |
| `git ls-remote --exit-code --heads origin "$branch"` | Verifies if the remote branch exists before attempting to set upstream. |
| `git branch --set-upstream-to="origin/$branch"` | Automatically sets up tracking if it's missing but the remote branch exists. |
| `git pull --rebase origin "$branch"` | Fetches and reapplies local commits on top of the remote branch. |
| `git push origin "$branch"` | Uploads the integrated changes to the remote repository. |
| `git rebase --abort` | Safety mechanism to clean up a repository if a sync conflict occurs. |
| `git remote` | Verifies the existence of the 'origin' remote before attempting network operations. |
