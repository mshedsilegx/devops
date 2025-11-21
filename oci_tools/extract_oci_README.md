# OCI Image Extraction Script (`extract_oci.sh`)

## 1. Application Overview and Objectives

`extract_oci.sh` is a powerful command-line utility designed to download and extract the contents of an OCI (Open Container Initiative) compliant container image. It provides a robust set of features for developers, security analysts, and DevOps engineers who need to inspect, verify, or analyze the filesystem of a container without running it.

The primary objectives of this script are:
- **Automated Extraction**: To reliably download an OCI image from a registry (or use a local copy) and extract its filesystem into a specified directory.
- **Advanced Inspection**: To provide tools for inspecting image metadata, such as entrypoints, exposed ports, and environment variables.
- **Integrity Verification**: To ensure the integrity of the image layers by verifying their SHA256 digests against the manifest.
- **Efficient Searching**: To offer a high-performance, parallel search capability for finding specific files within the extracted filesystem.
- **Flexibility and Control**: To give users fine-grained control over the extraction process, including the ability to reuse existing layers and manage temporary files.

## 2. Architecture and Design Choices

The script is designed with several key architectural principles in mind:

- **Modularity**: The script is broken down into distinct functions for each major task (e.g., `check_dependencies`, `search_files`, `inspect_metadata`, `verify_integrity`). This makes the code easier to read, maintain, and debug.
- **Strict Error Handling**: By using `set -eu`, the script is designed to fail fast and exit immediately if any command fails or an unset variable is referenced. This prevents unexpected behavior and makes troubleshooting more predictable.
- **Dependency Management**: A dedicated function (`check_dependencies`) checks for all required command-line tools before execution, providing clear error messages if a dependency is missing. This ensures a smoother user experience.
- **Subshell for Critical Operations**: The layer extraction loop is wrapped in a subshell `(...)` to reliably capture its exit status. This prevents the script from continuing with an incomplete or corrupt filesystem if one of the `tar` operations fails.
- **Parallelism for Performance**: The search functionality leverages `xargs -P` to run `find` in parallel, utilizing multiple CPU cores to significantly speed up file searches in large filesystems.
- **Security**: The search function includes a fix to escape the user-provided search pattern, mitigating the risk of command injection vulnerabilities.

## 3. Command-Line Arguments

The script's behavior is controlled through a set of command-line flags.

| Argument                | Type          | Default                                | Description                                                                                                   |
|-------------------------|---------------|----------------------------------------|---------------------------------------------------------------------------------------------------------------|
| `--image <SOURCE_IMAGE>`  | String        | *None*                                 | **(Mode Option)** Specifies the image to download and extract (e.g., `docker://ubuntu:22.04`).                  |
| `--layer-dir <LAYERS_DIR>`| String        | *None*                                 | **(Mode Option)** Specifies an existing directory with the manifest and layers, skipping the download.        |
| `--target-dir <DEST_DIR>` | String        | *None*                                 | **(Required)** The final, local directory where the merged filesystem will be extracted.                      |
| `--purge-layer-dir`     | Flag          | `false`                                | Automatically deletes the temporary layers directory after a successful extraction.                           |
| `--inspect`             | Flag          | `false`                                | Prints key image metadata (CMD, Entrypoint, Ports, etc.) from the image configuration file.               |
| `--verify`              | Flag          | `false`                                | Calculates SHA256 hashes of all layer files and compares them against the digests in the manifest.      |
| `--search <regexp>`     | String        | *None*                                 | Runs a parallel, recursive **filename/path search** using a regular expression.                               |
| `--quiet`               | Flag          | `false`                                | Suppresses all non-essential output, printing only errors. Useful for automation.                           |
| `--help`                | Flag          | `false`                                | Displays the help message and exits.                                                                          |
| `--examples`            | Flag          | `false`                                | Shows detailed usage examples and exits.                                                                      |

*Note: You must choose one of the **Mode Options** (`--image` or `--layer-dir`).*

## 4. Examples on How to Use

Here are several examples demonstrating the script's capabilities:

**1. Basic Download, Extraction, and Cleanup**
This command downloads the `node:20-alpine` image, extracts its filesystem to `./node_rootfs`, and automatically removes the temporary layer files upon completion.
```bash
./extract_oci.sh \
  --image docker://node:20-alpine \
  --target-dir ./node_rootfs \
  --purge-layer-dir
```

**2. Local Image Extraction with Search**
This command extracts a locally available image named `my_app:v1.2`, saves its filesystem to `./app_fs`, and searches for any file path ending in `/etc/nginx.conf`.
```bash
./extract_oci.sh \
  --image my_app:v1.2 \
  --target-dir ./app_fs \
  --search '.*\/etc\/nginx\.conf$'
```

**3. Inspection and Verification (No Extraction Focus)**
This is useful for quickly analyzing an image's metadata and verifying its contents without needing to keep the extracted filesystem.
```bash
./extract_oci.sh \
  --image docker://ubuntu:22.04 \
  --target-dir ./temp_output \
  --inspect \
  --verify \
  --purge-layer-dir
```

**4. Reusing Existing Layers (for Debugging or Efficiency)**
If you have already downloaded the layers, you can reuse them to speed up subsequent extractions or analyses.
```bash
./extract_oci.sh \
  --layer-dir ./busybox_layers \
  --target-dir ./extracted_busybox_fs \
  --quiet
```

**5. Quiet Mode for Automation (Extract and Search)**
This example demonstrates how to use the script in an automated workflow, extracting a large application and searching for license files with minimal console output.
```bash
EXTRACT_PATH="./large_app_root"
./extract_oci.sh \
  --image large_app:2.0 \
  --target-dir "$EXTRACT_PATH" \
  --search '.*license.*' \
  --quiet
```
