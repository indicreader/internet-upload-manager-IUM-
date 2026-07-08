```markdown
<div align="center">

# Bandwidth-Aware Universal Upload Manager (IUM)

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A lightweight Windows desktop application to queue and upload files to various cloud services seamlessly in the background.**

</div>

---

## 📖 Overview

**Bandwidth-Aware Universal Upload Manager** is a lightweight, single-file Python/Tkinter desktop application designed to let you reclaim control over your internet connection. Most asymmetric home networks suffer from high ping, stuttering video calls, or laggy gaming sessions whenever a large file upload chokes the upstream pipe. 

This utility solves that bottleneck by providing a centralized dashboard to queue local files for upload to **Google Drive, Telegram, or YouTube** while strictly honoring a manual bandwidth cap. Instead of reinventing complex API clients from scratch, it safely coordinates existing command-line tools as asynchronous background subprocesses—giving you a stable, robust tool that won't freeze your desktop interface.

---

## 🗂️ Table of Contents
- [✨ Key Features](#-key-features)
- [💻 Tech Stack](#-tech-stack)
- [📋 System Requirements](#-system-requirements)
- [🚀 Quick Start (Running from Source)](#-quick-start-running-from-source)
- [📦 Building the Standalone Executable (.exe)](#-building-the-standalone-executable-exe)
- [⚙️ External Tools & Destination Setup](#️-external-tools--destination-setup)
- [⚠️ Throttling Matrix & Limitations](#️-throttling-matrix--limitations)
- [📄 License](#-license)

---

## ✨ Key Features

* **Smart Destination Routing:** Mix and match uploads across Google Drive (via `rclone`), Telegram (via `curl`), and YouTube (via `youtube-upload`).
* **Granular Bandwidth Control:** A dedicated slider allows capping upload speeds dynamically from 0–10 MB/s (where 0 stands for unlimited speed). Throttling is handled natively at the subprocess layer.
* **Non-Blocking Execution Engine:** Upload tasks run inside a decoupled background worker thread using `subprocess` execution loops. The GUI remains completely fluid, and hidden command prompt windows are suppressed on Windows.
* **Sequential Queue Management:** Monitor items chronologically using a native `Treeview` layout that handles live tracking states: `Queued`, `Uploading`, `Done`, or `Failed`.
* **Live CLI Console Output Panel:** A transparent logs view pane displays the precise command-line query being executed along with real-time process stdout/stderr updates.
* **Dynamic Customization Engine:** Includes a native Light/Dark mode toggle paired with 4 custom accent colors. Theme preferences update instantly and survive sessions via local JSON configuration persistence.
* **Guided Setup Handholding:** The Settings dialogue maps out every required API field with plain-English hints. It embeds rapid hyperlinks that launch the exact external consoles needed (`@BotFather`, Google Cloud Console, etc.) to fetch your keys.
* **Adaptive File Ingestion:** Supports drag-and-drop mechanics using `tkinterdnd2`. If the library isn't found on the system, the application falls back gracefully to a standard file explorer dialogue without crashing.

---

## 💻 Tech Stack

* **Language:** Python 3.9+
* **GUI Engine:** Standard Library `Tkinter` (Zero external heavy visual framework wrappers like PyQt/PySide required)
* **Asynchrony Engine:** `threading` & `subprocess` pipe streams
* **Configuration Layer:** Localized JSON profile state files
* **Optional Extension:** `tkinterdnd2` (for drag-and-drop detection)

---

## 📋 System Requirements

The script depends on native operating system tools to perform the network heavy lifting. You must configure the binary paths for whichever platform you intend to route files to:

1. **Windows 10/11** (Ships natively with `curl` used for Telegram uploads)
2. **Rclone** (Required for Google Drive uploads) -> [Download Here](https://rclone.org/downloads/)
3. **youtube-upload CLI** (Required for YouTube uploads) -> Installed via Python package manager (`pip install youtube-upload`)

---

## 🚀 Quick Start (Running from Source)

1. Clone this repository onto your machine:
   ```bash
   git clone [https://github.com/your-username/your-repository-name.git](https://github.com/your-username/your-repository-name.git)
   cd your-repository-name

```

2. *(Optional)* Install the drag-and-drop extension library if you want drag functionality:
```bash
pip install tkinterdnd2

```


3. Launch the application shell from your source code root directory:
```bash
python main.py

```



---

## 📦 Building the Standalone Executable (.exe)

You can compress the script into a single, portable Windows application that runs independently without a Python terminal environment using PyInstaller.

1. Install PyInstaller into your development environment:
```bash
pip install pyinstaller

```


2. Compile the package using the optimized headless flags:
```bash
pyinstaller --onefile --windowed --name="UploadManager" main.py

```


*Note: If you are utilizing `tkinterdnd2`, remember to include its hook references or data tracking flags so PyInstaller packages the dependencies correctly into your final `dist/` directory binary.*

---

## ⚙️ External Tools & Destination Setup

Every field in the configuration dialogue includes interactive shortcuts. Follow these setup workflows to provision access:

### ☁️ Google Drive (via Rclone)

* **What you need:** An configured rclone remote name.
* **Setup Workflow:** Download `rclone`, open a standard terminal window, type `rclone config`, and follow the steps to link your Google Account. Input that exact profile target label string inside the Settings panel.

### 💬 Telegram (via Bot API)

* **What you need:** A Bot Token and Target Chat ID.
* **Setup Workflow:** 1. Open Telegram, search for `@BotFather`, and type `/newbot` to generate an authorized API wrapper secret.
2. Message your new bot, or add it to a private group chat.
3. Query `@userinfobot` or copy the group identification code to pull your numerical destination Chat ID, then save both variables into the Settings profile.

### 📺 YouTube (via youtube-upload)

* **What you need:** A Google Cloud Developer App `client_secrets.json` profile and an authenticated OAuth token cache path.
* **Setup Workflow:** Access your Google Cloud Console page, construct a new project container, whitelist the YouTube Data API v3, and download your desktop credentials file configuration directly to your local file path workspace.

---

## ⚠️ Throttling Matrix & Limitations

### Execution & Limitation Realities

* **Sequential Execution Paradigm:** Uploads are explicitly processed **one at a time**. Parallel channel multi-streaming is disabled by design to prevent bulk task threading conflicts from causing buffer drop timeouts.
* **The YouTube Throttling Flag Gap:** The third-party underlying `youtube-upload` command-line ecosystem lacks native upload speed management flags. The tool will warn you inside the interface whenever you route a file to YouTube while a bandwidth cap is active.

### Native Speed & Size Limitations Matrix

| Destination Service | Underlying Subprocess Engine | Bandwidth Throttling Support | Hard File Size Boundary Constraints |
| --- | --- | --- | --- |
| **Google Drive** | `rclone copy` | **YES** (`--bwlimit`) | Evaluated by your remaining cloud quota limits |
| **Telegram** | `curl -F` | **YES** (`--limit-rate`) | **50 MB Maximum limit** per file (Enforced strictly by the Telegram Bot API) |
| **YouTube** | `youtube-upload` | **NO** *(Warning Displayed)* | Subjected to standard Google verification account tiers |

---

## 📄 License

This software ecosystem is released under the terms of the **MIT License**. For complete copyright ownership layout declarations, read the tracking [LICENSE](https://www.google.com/search?q=LICENSE) file profile inside this repository directory structure.

```

```
