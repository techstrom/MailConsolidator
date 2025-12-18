# MailConsolidator

[日本語版 (Japanese)](README_ja.md) | [English](README_en.md)

MailConsolidator is a Python application that consolidates email from multiple source accounts (POP3/IMAP) into a single destination IMAP mailbox.

Starting in **January 2026**, Google states that Gmail will no longer support fetching messages from third-party accounts into Gmail via POP using **“Check mail from other accounts”** in Gmail settings. MailConsolidator is intended as a practical alternative: it fetches mail from your source accounts and uploads it to the destination IMAP server (including Gmail), so you can continue managing messages in one place.

## Table of Contents

* [Overview](#overview)
* [Key Features](#key-features)
* [Requirements](#requirements)
* [Installation](#installation)

  * [Windows (Recommended)](#windows-recommended)
  * [From Source (Developers)](#from-source-developers)
* [Usage](#usage)

  * [GUI Mode](#gui-mode)
  * [Startup Modes](#startup-modes)
  * [Options](#options)
  * [Daemon Management](#daemon-management)
* [Gmail Notes](#gmail-notes)
* [Configuration](#configuration)

  * [File Location](#file-location)
  * [Schema](#schema)
  * [Field Reference](#field-reference)
* [Processing Behavior](#processing-behavior)
* [Troubleshooting](#troubleshooting)
* [Documentation](#documentation)
* [Security Notes](#security-notes)
* [License](#license)

## Why MailConsolidator

Google has announced that, starting in **January 2026**, Gmail will no longer support fetching messages from third-party accounts into Gmail via POP using the **“Check mail from other accounts”** feature. This change affects users who have relied on Gmail to periodically retrieve mail from external POP servers and manage all messages within a single Gmail inbox.

MailConsolidator is designed to fill this gap. Instead of relying on Gmail’s built-in POP fetching, it independently retrieves messages from source mail servers (POP3 or IMAP) and uploads them to a destination IMAP server, including Gmail. This approach preserves a centralized inbox workflow while avoiding dependency on deprecated Gmail functionality.

In short, MailConsolidator provides:

* Continuity for workflows impacted by Gmail’s POP deprecation
* Explicit control over mail retrieval, retention, and scheduling
* A provider-agnostic solution that works with any standard POP3/IMAP server

## Overview

MailConsolidator retrieves messages from multiple mail servers and transfers them to a specified IMAP server, enabling centralized mail management. It supports both a GUI and a command-line interface, and it can run automatically on a schedule.

## Key Features

* **Multi-protocol sources**: Fetch from POP3 and IMAP
* **Unread-only IMAP fetching**: Efficiently fetch only unread messages for IMAP sources
* **Scheduled execution**: Run consolidation at a configurable interval
* **Real-time status**: Monitor processing status in the GUI
* **System tray integration (Windows)**: Run in the background from the Windows system tray
* **Single-instance behavior**: When already running, a new launch brings the existing GUI to the foreground (via IPC)
* **Per-source retention policy**: Choose whether to keep or delete messages on the source server
* **SSL/TLS support**: Secure connections
* **Windows installer**: Optional installer for easier setup

## Requirements

* Python 3.7 or later
* PyYAML
* psutil
* cryptography
* pystray (Windows system tray)
* Pillow (image handling)
* certifi (CA bundle for SSL)

## Installation

### Windows (Recommended)

1. **Download the installer**

   * `MailConsolidator-Setup-1.0.0.exe` from GitHub Releases:

     * [https://github.com/techstrom/MailConsolidator/releases/download/v1.0.0/MailConsolidator-Setup-1.0.0.exe](https://github.com/techstrom/MailConsolidator/releases/download/v1.0.0/MailConsolidator-Setup-1.0.0.exe)

2. **Run the installer**

   * Double-click the installer and follow the wizard.

3. **Launch**

   * Start from the Start menu or desktop shortcut.

### From Source (Developers)

1. Clone the repository:

```bash
git clone <repository-url>
cd MailConsolidator
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run:

```bash
python main.py
```

## Usage

### GUI Mode

Start the GUI:

```bash
python main.py
```

You may also run `MailConsolidator.exe` from the repository’s `dist` folder (if available).

**Single-instance behavior**: If the application is already running, a new launch will not start a second instance. Instead, it will bring the existing GUI window to the foreground and keep background tasks running.

#### GUI Workflow

1. **Destination Settings**

   * Enter destination IMAP server details
   * Click **Save Settings**

2. **Source Settings**

   * Add one or more source accounts
   * Provide protocol (POP3/IMAP), server information, and credentials
   * Configure **Delete after move** per account

3. **Execution Panel**

   * **Run Now**: Execute consolidation immediately
   * **Start/Stop Scheduled Run**: Toggle periodic execution (minutes)

     * **Auto-save**: Changing the interval and leaving the field automatically writes to the config file
   * **Exit Application**: Fully terminate MailConsolidator
   * **Status Monitor**: View processing status in real time

4. **Window Close (×)**

   * Choose one:

     * **Exit Application** (terminate)
     * **Run in Background** (hide window, stay in system tray)
     * **Cancel**

### Startup Modes

#### Default Startup (Background)

Starts the GUI in the background and returns control to the shell immediately:

```bash
python main.py
```

On Windows, the system tray icon provides:

* Show/Hide Window
* Toggle Scheduled Run
* Exit

#### GUI Foreground Mode (Verbose)

Starts the GUI and prints detailed logs to the console:

```bash
python main.py -v
```

#### Daemon Mode (No GUI)

Runs in the background without opening the GUI:

```bash
python main.py -d
```

### Options

* `-d`, `--daemon`: Run in daemon mode (no GUI)
* `-k`, `--kill`: Stop a running daemon process
* `-c`, `--config`: Path to the configuration file

  * Default (Windows): `%APPDATA%\MailConsolidator\config.yaml`
  * Default (Unix-like): `~/.config/MailConsolidator/config.yaml`
* `-v`, `--verbose`: Print verbose logs (GUI mode)
* `-l`, `--log-file`: Write logs to the specified file

Examples:

```bash
# Default: GUI starts in the background
python main.py

# Write logs to a file
python main.py -l app.log

# GUI foreground with console logs
python main.py -v

# Daemon mode with log file
python main.py -d -l daemon.log

# Stop a running daemon
python main.py -k
```

### Daemon Management

You can stop a background daemon using:

1. **System tray menu** (Windows GUI mode)
2. **Exit Application** button in the GUI
3. The `-k` option:

   ```bash
   python main.py -k
   ```
4. Terminate the process directly:

   * Windows: Task Manager
   * Unix-like: `kill`

The daemon state is tracked via a `mailconsolidator.pid` file in the system temporary directory.

## Gmail Notes

### POP-based fetching in Gmail

Google has announced that, starting January 2026, Gmail will no longer support fetching emails from third-party accounts into Gmail via POP using **“Check mail from other accounts”**.

### Gmail App Password

If your Gmail account has 2-Step Verification enabled, use a **Google App Password** instead of your regular password.

### Gmail IMAP Settings

Verify these settings:

* IMAP access: enabled (Gmail Settings → *Forwarding and POP/IMAP*)
* Host: `imap.gmail.com`
* Port: `993`
* SSL/TLS: enabled

## Configuration

### File Location

The configuration file is saved automatically in a platform-appropriate location:

* **Windows**: `%APPDATA%\MailConsolidator\config.yaml`
* **Unix-like**: `~/.config/MailConsolidator/config.yaml`

If an older `config.yaml` exists in the startup directory, it will be copied to the new location on first launch (the original file is not deleted).

You can override the path with `-c`:

```bash
python main.py -c "C:\custom\path\to\config.yaml"
```

### Schema

```yaml
interval: 3  # scheduled execution interval (minutes)

destination:
  host: imap.example.com
  port: 993
  user: dest_user@example.com
  password: your_password_or_app_password
  ssl: true
  folder: INBOX

sources:
  - protocol: imap  # or pop3
    host: imap.gmail.com
    port: 993
    user: source@gmail.com
    password: your_gmail_app_password
    ssl: true
    folder: INBOX  # IMAP only
    delete_after_move: false  # true to delete after transfer

  - protocol: pop3
    host: pop.example.com
    port: 995
    user: source2@example.com
    password: password
    ssl: true
    delete_after_move: true
```

### Field Reference

#### `destination`

* `host`: IMAP server hostname
* `port`: Port (typically 993)
* `user`: Username (email address)
* `password`: Password (use an app password for Gmail)
* `ssl`: Use SSL/TLS (`true` recommended)
* `folder`: Destination folder (default: `INBOX`)

#### `sources`

* `protocol`: `imap` or `pop3`
* `host`: Mail server hostname
* `port`: POP3 (typically 995) / IMAP (typically 993)
* `user`: Username (email address)
* `password`: Password (app password for Gmail)
* `ssl`: Use SSL/TLS (`true` recommended)
* `folder`: Source folder (IMAP only; default: `INBOX`)
* `delete_after_move`: Whether to delete messages from the source after transfer

  * `true`: Delete (recommended for POP3)
  * `false`: Keep (recommended for IMAP; messages are marked as read)

## Processing Behavior

### IMAP + `delete_after_move: false`

1. Fetch unread messages only
2. Upload to the destination IMAP server
3. Mark as read on the source server
4. Next run will skip those messages

### IMAP + `delete_after_move: true`

1. Fetch unread messages only
2. Upload to the destination IMAP server
3. Delete from the source server

### POP3 Notes

POP3 does not have a read/unread concept. If `delete_after_move: false`, the same messages may be fetched repeatedly. For POP3 sources, `delete_after_move: true` is strongly recommended.

## Troubleshooting

### Authentication failures

**Symptom**: `[AUTHENTICATIONFAILED] Invalid credentials`

**Actions**:

1. For Gmail, confirm you are using an **App Password** (not your regular password)
2. Ensure the password contains no spaces
3. Confirm that 2-Step Verification is enabled

### Duplicate messages

* IMAP: confirm that messages are marked as read when `delete_after_move: false`
* POP3: switch to `delete_after_move: true`

### Connection issues

1. Verify host and port
2. Confirm SSL/TLS configuration (`ssl: true` for Gmail)
3. Check firewall rules
4. Confirm IMAP access is enabled

### SSL error when running the EXE

**Symptom**: `[Errno 2] No such file or directory: ... base_library.zip`

**Resolution**:
Recent versions address this by using `certifi`. Rebuild with:

```bash
pip install certifi
pyinstaller MailConsolidator.spec
```

## Documentation

* [Requirements Definition (REQUIREMENTS.md)](./REQUIREMENTS.md)
* [Program Specification (SPECIFICATION.md)](./SPECIFICATION.md)

## Security Notes

* The configuration file (`config.yaml`) stores passwords in encrypted form; however, file system permissions still matter. Restrict access to your user account.
* For accounts with high message volume, the first run may take time.
* Mail servers may enforce connection-rate limits; aggressive polling can result in temporary blocking.

## License

This project is released under the [MIT License](./LICENSE).
