# Git Autosync - Execution Flow & Architecture Charts

This document provides a visual and structured breakdown of the `git_autosync.sh` script's execution flow, based on the system codemap.

## 1. Script Initialization and Argument Processing
The main entry point that parses command-line arguments and sets up the execution environment.

```mermaid
graph TD
Start --> ParseArgs["[1a] ParseArgs"]
ParseArgs --> LogRedirection["[1e] Log Redirection"]
LogRedirection --> Validate["[1b] Validate"]
Validate -- Fail --> Usage
Validate -- Pass --> SetupEnv
SetupEnv --> CreateTemp["[1c] CreateTemp"]
SetupEnv --> SetGitMode
SetupEnv --> RegisterSignals["[1d] RegisterSignals"]
RegisterSignals --> Discovery
```

### Key Locations
| ID | Title | Description | Code | Path:Line |
|:---|:---|:---|:---|:---|
| **1a** | Argument Parsing Loop | Iterates through command-line arguments to configure sync behavior | `while [[ $# -gt 0 ]]` | `git_autosync.sh:69` |
| **1b** | Base Directory Validation | Ensures required base folder parameter provided | `if [[ -z "$BASE_DEV_DIR" ]]` | `git_autosync.sh:147` |
| **1c** | Temporary Directory Creation | Creates temp directory for parallel process communication | `mktemp -d` | `git_autosync.sh:155` |
| **1d** | Signal Handler Setup | Registers cleanup function for graceful shutdown | `trap cleanup EXIT...` | `git_autosync.sh:178` |
| **1e** | Log File Redirection | Redirects all output to file if --logfile is specified | `exec > >(tee -a ...)` | `git_autosync.sh:142` |

---

## 2. Repository Discovery and Processing Loop
Finds all git repositories recursively and orchestrates their processing.

```mermaid
graph TD
Discovery --> FindCmd["[2e] FindCmd"]
FindCmd --> Loop["[2a] Loop"]
Loop --> ExtractPath["[2b] ExtractPath"]
ExtractPath --> Progress
Progress --> ModeCheck
ModeCheck -- Parallel --> ParallelLaunch["[2c] ParallelLaunch"]
ParallelLaunch --> LimitCheck["[2d] LimitCheck"]
LimitCheck -- Yes --> Wait
Wait --> LimitCheck
LimitCheck -- No --> Next
ModeCheck -- No --> SyncDirect
SyncDirect --> Next
Next --> WaitAll
```

### Key Locations
| ID | Title | Description | Code | Path:Line |
|:---|:---|:---|:---|:---|
| **2a** | Repository Discovery Loop | Iterates through all .git directories found recursively | `while IFS= read...` | `git_autosync.sh:406` |
| **2b** | Directory Extraction | Extracts parent directory path from .git location | `dirname` | `git_autosync.sh:408` |
| **2c** | Parallel Process Launch | Starts sync_repo function in background for parallel execution | `sync_repo &` | `git_autosync.sh:418` |
| **2d** | Job Limit Management | Waits when max parallel jobs reached | `jobs -p | wc -l` | `git_autosync.sh:427` |
| **2e** | Find Command Execution | Finds all .git directories using null-delimited output | `find -name ".git"` | `git_autosync.sh:434` |

---

## 3. Single Repository Synchronization Logic
Core git operations performed on each repository.

```mermaid
sequenceDiagram
participant S as Script
participant G as Git Repository
participant R as Remote (Origin)
S->>G: [3a] Change to directory
S->>G: [3b] Detect Local Changes
alt Changes Detected
S->>G: [3c] git add -A
S->>G: git commit -m "Auto-sync..."
end
S->>G: Get Current Branch
S->>G: Check Upstream Tracking
S->>R: Verify Remote Branch exists
S->>G: [3d] Pull with Rebase
G->>R: Fetch & Rebase
alt Conflict?
S->>G: git rebase --abort
else Success
S->>G: [3e] Push to Remote
G->>R: Upload Changes
end
S->>S: Log Outcome & Status
```

### Key Locations
| ID | Title | Description | Code | Path:Line |
|:---|:---|:---|:---|:---|
| **3a** | Directory Navigation | Changes to repository directory with error handling | `pushd` | `git_autosync.sh:201` |
| **3b** | Local Changes Detection | Checks for uncommitted changes using porcelain format | `git status --porcelain` | `git_autosync.sh:223` |
| **3c** | Stage All Changes | Stages all modifications including deletions and new files | `git add -A` | `git_autosync.sh:238` |
| **3d** | Pull with Rebase | Pulls remote changes using rebase strategy | `git pull --rebase` | `git_autosync.sh:302` |
| **3e** | Push to Remote | Pushes local commits to remote repository | `git push` | `git_autosync.sh:324` |

---

## 4. Error Handling and Conflict Resolution
Manages errors, conflicts, and cleanup operations during synchronization.

```mermaid
graph TD
Sync --> Pull
Pull --> ExitCheck["[4a] ExitCheck"]
ExitCheck -- No --> ConflictCheck["[4b] ConflictCheck"]
ConflictCheck -- Yes --> Abort["[4c] Abort"]
Abort --> Fail
Signal --> Cleanup
Cleanup --> JobsCheck
JobsCheck -- Yes --> Terminate["[4e] Terminate"]
JobsCheck -- No --> PurgeTemp
Terminate --> PurgeTemp
pids["[4d] Collect PIDs"]
```

### Key Locations
| ID | Title | Description | Code | Path:Line |
|:---|:---|:---|:---|:---|
| **4a** | Pull Error Detection | Checks if pull operation failed | `if [[ $pull_exit -ne 0 ]]` | `git_autosync.sh:311` |
| **4b** | Rebase Conflict Detection | Detects ongoing rebase conflicts | `if [[ -d ".git/rebase..." ]]` | `git_autosync.sh:312` |
| **4c** | Rebase Abort | Cleans up failed rebase to restore repository state | `git rebase --abort` | `git_autosync.sh:314` |
| **4d** | Background Process Collection | Gathers PIDs of all background jobs for cleanup | `jobs -p` | `git_autosync.sh:166` |
| **4e** | Process Termination | Gracefully terminates background processes on interrupt | `kill -TERM` | `git_autosync.sh:170` |

---

## 5. Results Aggregation and Reporting
Collects and displays results from parallel repository processing.

```mermaid
graph TD
Wait["[5a] Wait"] --> ProcessLoop["[5b] ProcessLoop"]
ProcessLoop --> ReadStatus["[5c] ReadStatus"]
ReadStatus --> DisplayLog
DisplayLog -- Yes --> CatLog
DisplayLog -- No --> Classify["[5d] Classify"]
CatLog --> Classify
Classify --> Next
Next --> Report["[5e] Report"]
```

### Key Locations
| ID | Title | Description | Code | Path:Line |
|:---|:---|:---|:---|:---|
| **5a** | Wait for Completion | Waits for all background processes to finish | `wait` | `git_autosync.sh:437` |
| **5b** | Results Processing Loop | Iterates through all processed repositories | `for (( i=1; i<=... ))` | `git_autosync.sh:443` |
| **5c** | Status Reading | Reads processing status from temp files | `cat "$status_f"` | `git_autosync.sh:449` |
| **5d** | Result Classification | Categorizes results for summary statistics | `case "$outcome" in` | `git_autosync.sh:458` |
| **5e** | Summary Report | Displays final statistics of sync operation | `echo "Total..."` | `git_autosync.sh:467` |
