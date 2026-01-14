# Citrix Workspace Management Tool

## Application Overview and Objectives
The `CitrixTool.ps1` is a PowerShell-based command-line utility designed to automate the backup and restoration of Citrix Workspace configuration settings. In complex environments, Citrix Workspace can often experience configuration drift or corrupted identity caches. This tool provides a reliable way to:
- **Preserve User Experience**: Capture personalized Citrix Receiver settings and AuthManager identity tokens.
- **Simplify Migration/Recovery**: Easily move Citrix configurations between machines or restore to a known good state.
- **Ensure Operational Consistency**: Automate the tedious process of stopping services, exporting registry keys, and managing file locks.

## Architecture and Design Choices
The tool is built with production-grade reliability in mind, utilizing the following design patterns:
- **Atomicity**: Operations are performed in a staging directory (`$env:TEMP`) and only finalized (zipped or moved) upon successful completion of all sub-steps.
- **Robust Error Handling**: Employs `try-catch-finally` blocks to ensure that even if a failure occurs, the system is left in a clean state with no dangling temporary files.
- **Process Management**: Restores are prefixed with a forced termination of all Citrix-related processes to release file locks on the `AuthManager` database files.
- **Parameter Sets**: Uses PowerShell Parameter Sets to ensure that `-Backup` and `-Restore` are mutually exclusive, preventing accidental misuse.
- **Observability**: Supports standard PowerShell `-Verbose` and `-Debug` flags via `[CmdletBinding()]` for deep troubleshooting.

## Command Line Arguments

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `-Backup` | `Switch` | `False` | Initiates the backup process. Mutually exclusive with `-Restore`. |
| `-Restore` | `Switch` | `False` | Initiates the restore process. Mutually exclusive with `-Backup`. |
| `-Path` | `String` | `$HOME\Desktop` (Backup) | For **Backup**: The directory where the ZIP will be saved.<br>For **Restore**: The full path to the backup ZIP file. |
| `-Verbose` | `Switch` | `False` | (Common Parameter) Displays detailed progress messages. |
| `-Debug` | `Switch` | `False` | (Common Parameter) Displays developer-level debugging information. |

## Examples

### 1. Simple Backup to Desktop
Saves a ZIP file named `<COMPUTERNAME>_citrixbackup_<TIMESTAMP>.zip` to your Desktop.
```powershell
.\CitrixTool.ps1 -Backup
```

### 2. Backup to a Specific Network Share
```powershell
.\CitrixTool.ps1 -Backup -Path "\\Server\Backups\Citrix"
```

### 3. Restore from a Specific Backup File
*Note: This will close any open Citrix applications.*
```powershell
.\CitrixTool.ps1 -Restore -Path "C:\Backups\MYPC_citrixbackup_20260114-103400.zip"
```

### 4. Running with Detailed Logging
```powershell
.\CitrixTool.ps1 -Restore -Path "C:\Backups\Citrix.zip" -Verbose
```
