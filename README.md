<img width="2816" height="1536" alt="logo" src="https://github.com/user-attachments/assets/40354b6f-9b14-4693-835b-e9209b8677d4" />

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
Destination Service,Underlying Subprocess Engine,Bandwidth Throttling Support,Hard File Size Boundary Constraints
Google Drive,rclone copy,YES (--bwlimit),Evaluated by your remaining cloud quota limits
Telegram,curl -F,YES (--limit-rate),50 MB Maximum limit per file (Enforced strictly by the Telegram Bot API)
YouTube,youtube-upload,NO (Warning Displayed),Subjected to standard Google verification account tiers

---

## 🚀 Quick Start (Running from Source)

1. Clone this repository onto your machine:
   ```bash
   git clone [https://github.com/your-username/your-repository-name.git](https://github.com/your-username/your-repository-name.git)
   cd your-repository-name
