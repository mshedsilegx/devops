# Documentation for `set_nomodeset.sh`

## Application Overview and Objectives

The `set_nomodeset.sh` script is a bash utility designed to automate the configuration of Linux kernel boot parameters, specifically for headless servers or systems encountering graphics driver compatibility issues. 

**Core Objectives:**
*   **Enforce `nomodeset`**: Ensures the `nomodeset` parameter is present in the `GRUB_CMDLINE_LINUX` setting within the GRUB configuration. This instructs the kernel to rely on BIOS modes rather than loading hardware-specific video drivers during boot.
*   **System Compatibility**: Automatically adapts to different Linux distribution families (RHEL/CentOS/Rocky vs. Debian/Ubuntu) to apply changes correctly.
*   **Reliability**: Implements idempotent operations to safely run multiple times without creating duplicate entries or configuration errors.

## Architecture and Design Choices

*   **Idempotent Configuration**: 
    The script uses a two-step process for modifying configuration:
    1.  **Cleanup**: It proactively removes any existing `nomodeset` entries using regex-based substitution.
    2.  **Injection**: It inserts `nomodeset` at the beginning of the argument string.
    This design prevents "drift" or duplication (e.g., `nomodeset nomodeset`) if the script is run multiple times.

*   **OS Family Abstraction**:
    Instead of hardcoding commands for a single distro, the script parses `/etc/os-release` to identify the OS family. This determines the appropriate command to regenerate the GRUB bootloader configuration:
    *   **RHEL/Fedora Family**: Uses `grub2-mkconfig -o /boot/grub2/grub.cfg`
    *   **Debian/Ubuntu Family**: Uses `update-grub`

*   **Error Handling**:
    A centralized `check_error` function wraps critical operations. This ensures that if any step fails (like missing config files or a failed `sed` command), the script terminates immediately with an error message, preventing partial or corrupted configurations.

*   **Direct File Manipulation**:
    The script uses `sed` (Stream Editor) for in-place editing of `/etc/default/grub`. The specific regex pattern `/^GRUB_CMDLINE_LINUX=/s/="="nomodeset /` is designed to insert the parameter immediately after the opening quote of the variable assignment (assuming standard `KEY="VALUE"` format).

## Command Line Arguments

The script currently takes no command line arguments. All configuration is determined dynamically or hardcoded as constants within the script.

| Argument | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| None | This script does not accept flags or parameters. | N/A | N/A |

## Examples on how to use

**Prerequisites**: The script requires root privileges to modify system files (`/etc/default/grub`) and run bootloader update commands.

### 1. Execution
Run the script using `sudo`:

```bash
cd os_sys
chmod +x set_nomodeset.sh
sudo ./set_nomodeset.sh
```

**Expected Output:**
```text
--- Detected OS Family: DEBIAN ---
Processing /etc/default/grub...
Inserted 'nomodeset' into GRUB_CMDLINE_LINUX.
Running OS-specific GRUB update command: update-grub
...
GRUB configuration updated successfully.
The change will take effect on the next reboot.
```

### 2. Verification
After execution, verify the content of the GRUB default configuration:

```bash
grep GRUB_CMDLINE_LINUX /etc/default/grub
```
**Output should look like:**
```text
GRUB_CMDLINE_LINUX="nomodeset quiet splash"
```

### 3. Apply Changes
Reboot the server for the kernel parameter to take effect:

```bash
sudo reboot
```
