# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2025/10/06 - 9b97926]

### Added
- **New `init-and-push` Sync Method**: Introduced a new sync method (`--sync-method=init-and-push`) to initialize a Git repository from a local directory and push its contents to a new or empty remote repository. This was the core feature request of the initial task.
- **Flexible Logging Options**:
    - Added a `--log-file=<file>` argument to redirect all script output (stdout and stderr) to a specified log file. It defaults to a file in the system's temporary directory.
    - Added a `--log-console` flag to override file logging and force all output to be displayed on the console.

### Changed
- **Improved Method Naming for Clarity**:
    - Renamed the `init-and-sync` method to `clone-and-pull` to more accurately describe its action of cloning a remote repository.
    - Renamed the `pull-push` method to `pull-and-push` for better consistency with other method names.
- **Generalized Commit Message Argument**: Replaced the specific `--merge-commit-message` with a more generic `--custom-commit-message` argument. This new flag can be used to specify the commit message for any commit the script creates, including merge commits and the initial commit for `init-and-push`.
- **Enhanced `--local-dir` Functionality**: The `--local-dir` argument now serves as a generic working directory. For most operations, the script will change into this directory before execution. For the `clone-and-pull` method, it retains its original purpose of specifying the clone destination.

### Removed
- **Redundant Pull Strategy**:
    - Removed the `--pull-method=pull` option, as it was less explicit than the `fetch-merge` and `fetch-rebase` options.
    - Removed the `--pull-strategy` argument, which was only used with the now-deleted `pull` method. This simplifies the script and makes its behavior more predictable.
