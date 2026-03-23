# IIS Delegation Toolset

## Overview and Objectives
The **IIS Delegation Toolset** provides a secure, automated way to delegate full IIS and Application Pool management to a specific non-administrative Active Directory group. 

The primary objective is to enable DevOps autonomy by allowing designated users to create sites, modify pools, and manage configurations without granting them local Administrator rights on the Windows Server.

## 2. Command Line Arguments

All three scripts in the toolset share a common set of parameters where applicable.

| Parameter | Script(s) | Type | Mandatory | Default | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `-GroupName` | All | `[string]` | Yes | - | The name of the AD group to delegate permissions to (e.g., `DOMAIN\Group`). |
| `-BackupLocation` | Set, Undo | `[string]` | No | `%TEMP%\IISDelegation\backup` | The directory where IIS configuration backups will be stored. |

## 3. Usage Examples

### 3.1. Setting Up Delegation
Run this script from an **Elevated (Administrator)** PowerShell session to apply the delegation.

```powershell
# Default backup location
.\IISDelegationSet.ps1 -GroupName "CORP\IIS_Managers"

# Custom backup location
.\IISDelegationSet.ps1 -GroupName "CORP\IIS_Managers" -BackupLocation "C:\Backups\IIS"
```

### 3.2. Validating Permissions
Run this script as a member of the **Delegated Group** (Non-Elevated) to verify the setup.

```powershell
.\IISDelegationValidate.ps1 -GroupName "CORP\IIS_Managers"
```

### 3.3. Reverting Delegation
Run this script from an **Elevated (Administrator)** PowerShell session to remove all delegated permissions.

```powershell
.\IISDelegationUndo.ps1 -GroupName "CORP\IIS_Managers"
```

## 4. Key Features
- **Comprehensive:** Unlocks 17+ IIS configuration sections (Auth, Handlers, etc.).
- **Safe:** Performs recursive backups before any changes.
- **Traceable:** Color-coded console logging for all operations.
- **Auditable:** Built-in validation script with deep ACL and functional write tests.
