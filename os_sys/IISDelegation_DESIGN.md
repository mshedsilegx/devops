This document outlines the requirements and technical implementation for delegating full IIS and Application Pool management to a specific non-administrative Active Directory group (e.g., **DOMAIN\GROUPNAME**).

---

## 1. Executive Summary
The goal is to allow members of a delegated Active Directory group (e.g., **DOMAIN\GROUPNAME**) to perform all IIS administrative tasks—including creating/modifying sites, stopping/starting Application Pools, and editing global configuration—without granting them local **Administrator** rights on the Windows Server. This ensures the principle of least privilege while enabling DevOps autonomy.

---

## 2. Technical Requirements
To achieve full management capability, four distinct layers of Windows security must be addressed:

| Layer | Requirement | Reason |
| :--- | :--- | :--- |
| **File System** | Modify access to `%windir%\system32\inetsrv\config` | To read/write `applicationHost.config` and `administration.config`. |
| **Service Control** | Start/Stop/Query for `W3SVC` and `WAS` | `WAS` (Windows Process Activation Service) governs App Pools. |
| **Registry** | Full Control of `HKLM\SOFTWARE\Microsoft\InetStp` | Required by IIS management APIs and PowerShell modules. |
| **IIS Schema** | `overrideModeDefault="Allow"` for key sections | To "unlock" sections so non-admins can commit changes. |
| **Work Folders** | Modify access to `C:\inetpub\temp\appPools` | Required for worker processes (`w3wp.exe`) to initialize. |

---

## 3. Implementation Details & Technical Considerations

### 3.1. Backup Strategy
*   **Default Location:** `%TEMP%\IISDelegation\backup`
*   **Configurability:** All scripts must support a custom backup path via the `-BackupLocation` parameter.
*   **Execution:** A timestamped subfolder is created for each run. Configuration files are recursively copied before any modification occurs.

### 3.2. Security Considerations (Least Privilege)
*   **Group Name vs. SID:** ACLs are applied using the Group Name for readability in File Explorer, as per user preference.
*   **Modify vs. Full Control:** NTFS and Registry permissions are limited to "Modify" or "Full Control" only on specific required paths.
*   **SDDL Injection:** Service permissions for `W3SVC` and `WAS` are modified by appending an ACE `(A;;RPWPCR;;;SID)` to allow Start, Stop, and Query without full administrative rights.

### 3.3. Configuration Unlocking
The following sections are unlocked in `applicationHost.config` by setting `overrideModeDefault="Allow"` to ensure full management capability:
*   `system.applicationHost/applicationPools`
*   `system.applicationHost/sites`
*   `system.applicationHost/log`
*   `system.applicationHost/configHistory`
*   `system.webServer/defaultDocument`
*   `system.webServer/modules`
*   `system.webServer/handlers`
*   `system.webServer/security/authentication/anonymousAuthentication`
*   `system.webServer/security/authentication/windowsAuthentication`
*   `system.webServer/security/authentication/basicAuthentication`
*   `system.webServer/security/access`
*   `system.webServer/security/ipSecurity`
*   `system.webServer/httpCompression`
*   `system.webServer/staticContent`
*   `system.webServer/directoryBrowse`
*   `system.webServer/httpErrors`
*   `system.webServer/tracing/traceFailedRequests`

---

## 4. Operational Scripts
The implementation consists of three primary PowerShell scripts. 

### Execution Requirements:
*   **IISDelegationSet.ps1:** MUST be executed as **Administrator**.
*   **IISDelegationUndo.ps1:** MUST be executed as **Administrator**.
*   **IISDelegationValidate.ps1:** SHOULD be executed as a member of the **delegated group** (non-Administrator) to accurately validate permissions.

All scripts require the `-GroupName` parameter as a mandatory CLI argument.

### 4.1. IISDelegationSet.ps1 (The "Do" Script)
*   Performs backups.
*   Applies NTFS and Registry ACLs.
*   Injects Service SDDLs.
*   Unlocks configuration sections.
*   **Logging:** Provides explicit `[SUCCESS]` or `[ERROR]` feedback for every sub-operation.

### 4.2. IISDelegationUndo.ps1 (The "Rollback" Script)
*   Re-locks all configuration sections to `Deny`.
*   Resets `W3SVC` and `WAS` SDDLs to standard Windows defaults.
*   Removes the specific Group ACEs from NTFS and Registry.
*   Provides safety warnings about manual backup cleanup.

### 4.3. IISDelegationValidate.ps1 (The "Audit" Script)
*   **Deep ACL Check:** Verifies the actual presence of the Group ACE in filesystem and registry ACLs.
*   **Service Control Check:** Uses `sc.exe sdshow` to verify control access.
*   **Functional Test:** Safely toggles a non-destructive property (`autoStart`) on the `DefaultAppPool` to confirm write-path availability.

---

## 5. Operational Workflow
The following diagram illustrates how the delegated permissions interact to allow a non-admin user to manage the environment:



1.  **User Action:** A delegated group member runs `Start-WebAppPool`.
2.  **API Check:** The system verifies the user has **Service Control** rights for `WAS`.
3.  **Config Check:** The system verifies the user has **NTFS** rights to read the configuration.
4.  **Execution:** `WAS` starts the worker process and writes temporary data to `C:\inetpub\temp\appPools`.

---

## 5. Risk Mitigation & Rollback
* **UAC Constraint:** Users must still use "Run as Administrator" for PowerShell/CMD. This does not make them an admin; it simply tells Windows to use the "highest available" token (the ones we delegated).
* **Undo Script:** A dedicated script is provided to:
    1.  Re-lock all IIS sections listed in Section 3.3.
    2.  Reset Service SDDLs to the factory Windows default (`D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWLOCRRC;;;IU)(A;;CCLCSWLOCRRC;;;SU)`).
    3.  Remove the specific group ACEs from the File System (`C:\Windows\System32\inetsrv\config`, `C:\inetpub\temp\appPools`) and Registry (`HKLM\SOFTWARE\Microsoft\InetStp`).

---

## 6. Maintenance
It is recommended to re-run the **Verification Script** after any major Windows Update or IIS Role upgrade, as system updates can occasionally reset Service Security Descriptors (SDDLs) to their default state.

---
