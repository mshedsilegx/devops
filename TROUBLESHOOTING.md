# Troubleshooting Guide for git_sync.sh

This document provides solutions to common issues you may encounter when using the `git_sync.sh` script.

## Table of Contents
1.  [Lock File Exists](#1-lock-file-exists)
2.  [Authentication Failed](#2-authentication-failed)
3.  [Merge or Rebase in Progress](#3-merge-or-rebase-in-progress)
4.  [Detached HEAD State](#4-detached-head-state)
5.  [Permission Denied](#5-permission-denied)
6.  [Command Not Found](#6-command-not-found)

---

### 1. Lock Directory Exists

-   **Error Message**: `Lock directory found at /tmp/git_sync_<repo_hash>.lockdir. Another instance of git_sync.sh may be running for this repository.`
-   **Cause**: This error occurs if a previous run of the script for the same repository was interrupted or if another instance is currently running. The script creates a unique lock directory for each repository to prevent concurrent operations.
-   **Solution**:
    1.  First, verify that no other `git_sync.sh` process is running for this specific repository. You can check this using a command like `ps aux | grep git_sync.sh`.
    2.  If you are certain no other instance is running, you can safely remove the lock directory. It is typically located in the `/tmp` directory (or the directory specified by the `$TMPDIR` environment variable) and is named `git_sync_<repo_hash>.lockdir`. The error message will show the exact path.
    3.  To remove it, use the `rmdir` command with the full path from the error message:
        ```bash
        # Example:
        rmdir /tmp/git_sync_a1b2c3d4e5f6.lockdir
        ```
    4.  Rerun the script.

---

### 2. Authentication Failed

-   **Error Message**: `Permission denied (publickey).` or `fatal: Authentication failed for 'https://...'`
-   **Cause**: The script is unable to authenticate with the remote Git repository. This is common when using SSH or HTTPS without proper credential setup.
-   **Solution**:
    -   **SSH**: Ensure your SSH key is correctly added to your SSH agent (`ssh-add`) and registered with your Git provider (e.g., GitHub, GitLab).
    -   **HTTPS**: Use a Git credential helper to securely store your credentials. This is the recommended approach. You can configure it with:
        ```bash
        git config --global credential.helper store
        # Or use a more secure helper like 'cache' or a platform-specific one.
        ```
    -   Avoid embedding your username and password in the `GIT_REPO_URL`.

---

### 3. Merge or Rebase in Progress

-   **Error Message**: `A merge is currently in progress...` or `A rebase is currently in progress...`
-   **Cause**: The script has detected that the repository is in the middle of a merge or rebase, which prevents automated operations from running safely.
-   **Solution**:
    -   Manually resolve the ongoing process.
    -   To abort a **merge**:
        ```bash
        git merge --abort
        ```
    -   To abort a **rebase**:
        ```bash
        git rebase --abort
        ```
    -   If you want to complete the process, follow the instructions provided by Git to resolve conflicts, then commit the changes.

---

### 4. Detached HEAD State

-   **Warning Message**: `Detached HEAD state detected. Operations will be limited.`
-   **Cause**: The repository is not on a branch; it is checked out to a specific commit. In this state, you cannot push changes.
-   **Solution**:
    -   If you need to make changes and push them, you must be on a branch. You can create a new branch from the current commit:
        ```bash
        git checkout -b new-feature-branch
        ```
    -   If you intended to be on an existing branch, switch to it:
        ```bash
        git checkout main
        ```

---

### 5. Permission Denied

-   **Error Message**: `bash: ./git_sync.sh: Permission denied`
-   **Cause**: The script file does not have execute permissions.
-   **Solution**:
    -   Add execute permissions to the script:
        ```bash
        chmod +x git_sync.sh
        ```

---

### 6. Command Not Found

-   **Error Message**: `./git_sync.sh: command not found`
-   **Cause**: You are trying to execute the script from a directory where it is not located.
-   **Solution**:
    -   Ensure you are in the same directory as the script, or provide the full path to it.
    -   To run from the current directory, use:
        ```bash
        ./git_sync.sh --sync-method=...
        ```