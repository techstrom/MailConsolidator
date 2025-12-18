# MailConsolidator
[日本語版 (Japanese)](README_ja.md) | [English](README_en.md)

MailConsolidator is a Python application that consolidates emails from multiple email accounts (POP3/IMAP) into a single IMAP server.
Gmail will discontinue POP access (the ability to retrieve emails from other mail servers via POP) starting in January 2026, so this tool is designed as an alternative. By fetching emails from other POP servers and pushing them into Gmail via IMAP, you can continue consolidating external POP emails into Gmail just as before, as long as this application is running.

## Overview

MailConsolidator retrieves emails from multiple mail servers and forwards them to a specified IMAP server, enabling centralized email management. It supports both GUI and command-line interfaces and can be configured to run automatically at regular intervals.

## Key Features

* **Multiple protocol support**: Retrieve emails from both POP3 and IMAP
* **Unread-only retrieval**: Efficiently fetch only unread emails when using IMAP
* **Automatic execution**: Run email consolidation automatically at specified intervals
* **Real-time monitoring**: Monitor email processing status in real time via the GUI
* **System tray resident**: Runs in the background in the Windows system tray
* **Single-instance control**: If already running, the existing GUI is shown (via IPC)
* **Flexible deletion settings**: Choose whether to keep or delete emails on the source server
* **SSL/TLS encryption**: Secure communication support
* **Windows installer**: Easy installation via a Windows installer

## Requirements

* Python 3.7 or later
* PyYAML
* psutil
* cryptography
* pystray (for Windows system tray)
* Pillow (for image handling)
* certifi (for SSL certificates)

## Installation

### For Windows Users (Recommended)

You can easily install the application using the Windows installer:

1. **Download the installer**:

   * Download MailConsolidator-Setup-1.0.0.exe from the GitHub Releases page

2. **Run the installer**:

   * Double-click the downloaded installer
   * Follow the installation wizard

3. **Launch**:

   * Start the application from the Start menu or desktop icon

### For Developers (Run from Source)

1. Clone or download the repository:

```bash
git clone <repository-url>
cd MailConsolidator
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run as a Python script:

```bash
python main.py
```

## Usage

### GUI Mode (Recommended)

Launch the GUI to configure and run the application:

```bash
python main.py
```

If the application is already running, a new process will not be started. Instead, the existing GUI window will be brought to the foreground. Background tasks will not be interrupted.

## License

This project is released under the MIT License.
