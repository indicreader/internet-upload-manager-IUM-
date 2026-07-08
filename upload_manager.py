#!/usr/bin/env python3
"""
Bandwidth-Aware Universal Upload Manager
-----------------------------------------
Standalone Tkinter desktop app for Windows.

Queues local files and uploads them to:
  - Google Drive (via rclone)
  - Telegram    (via curl -> Bot API)
  - YouTube     (via the youtube-upload CLI)

Uploads run in a background thread (subprocess, no console window) so the
GUI never freezes. Files are processed one at a time so the bandwidth
limit you set actually applies to the whole queue.

See README.md for what to install before this will do anything, and for
how to build a no-console .exe with PyInstaller.
"""

import json
import os
import subprocess
import threading
import queue
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# --------------------------------------------------------------------------
# Optional drag-and-drop support (pip install tkinterdnd2). Falls back to
# Browse-button-only if it's not installed -- no hard dependency.
# --------------------------------------------------------------------------
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload_manager_config.json")

DEFAULT_CONFIG = {
    "rclone_remote": "gdrive:/Uploads",
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "youtube_client_secrets": "",
    "youtube_credentials_file": "",
    "theme": "Dark",
    "accent": "Blue",
}

DESTINATIONS = [
    "Google Drive (rclone)",
    "Telegram (Bot API)",
    "YouTube (youtube-upload)",
]

# Hides the console window that subprocess would otherwise flash on Windows.
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# ---- Theme + accent presets -----------------------------------------------
THEMES = {
    "Dark": {
        "bg": "#1e1e1e", "panel": "#252526", "fg": "#e0e0e0",
        "entry_bg": "#2d2d2d", "muted": "#888888",
        "ok": "#4caf50", "err": "#e5534b",
    },
    "Light": {
        "bg": "#f2f2f2", "panel": "#ffffff", "fg": "#1c1c1c",
        "entry_bg": "#ffffff", "muted": "#666666",
        "ok": "#2e7d32", "err": "#c62828",
    },
}

ACCENTS = {
    "Blue": "#3a86ff",
    "Green": "#43a047",
    "Purple": "#8b5cf6",
    "Rose": "#f43f5e",
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = DEFAULT_CONFIG.copy()
                cfg.update(json.load(f))
                return cfg
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def build_command(destination, file_path, bwlimit_mb, cfg):
    """Build the CLI command list for the chosen destination.
    Returns (cmd_list, warning_or_empty_string). Raises ValueError if
    required settings are missing."""

    if destination == "Google Drive (rclone)":
        cmd = ["rclone", "copy", file_path, cfg["rclone_remote"], "-P"]
        if bwlimit_mb > 0:
            cmd += ["--bwlimit", f"{bwlimit_mb}M"]
        return cmd, ""

    if destination == "Telegram (Bot API)":
        token = cfg["telegram_bot_token"]
        chat_id = cfg["telegram_chat_id"]
        if not token or not chat_id:
            raise ValueError("Telegram bot token / chat id not set. Open Settings first.")
        url = f"https://api.telegram.org/bot{token}/sendDocument?chat_id={chat_id}"
        cmd = ["curl", "-F", f"document=@{file_path}", url]
        if bwlimit_mb > 0:
            cmd += ["--limit-rate", f"{bwlimit_mb}M"]
        warning = "Note: Telegram's Bot API rejects files over 50MB (self-hosted Bot API server needed for more)."
        return cmd, warning

    if destination == "YouTube (youtube-upload)":
        secrets = cfg["youtube_client_secrets"]
        creds = cfg["youtube_credentials_file"]
        if not secrets or not creds:
            raise ValueError("YouTube client secrets / credentials file not set. Open Settings first.")
        title = os.path.splitext(os.path.basename(file_path))[0]
        cmd = [
            "youtube-upload",
            f"--client-secrets={secrets}",
            f"--credentials-file={creds}",
            f"--title={title}",
            "--privacy=private",
            file_path,
        ]
        warning = ""
        if bwlimit_mb > 0:
            warning = "Note: youtube-upload has no bandwidth-limit flag -- the MB/s slider is ignored for YouTube."
        return cmd, warning

    raise ValueError(f"Unknown destination: {destination}")


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, cfg, colors, on_save):
        super().__init__(parent)
        self.title("Settings")
        self.configure(bg=colors["bg"])
        self.resizable(False, False)
        self.cfg = cfg
        self.colors = colors
        self.on_save = on_save
        self.vars = {}

        # (config key, field label, plain-English hint, browse mode, help button text, help url)
        # browse mode: None = plain text entry, "open" = pick an existing file,
        # "save" = pick/create a file location.
        fields = [
            ("rclone_remote", "Rclone remote:path (e.g. gdrive:/Uploads)",
             "Create the remote once by running 'rclone config' in a terminal, then type its name here.",
             None, "rclone Drive setup guide", "https://rclone.org/drive/"),
            ("telegram_bot_token", "Telegram Bot Token",
             "Message @BotFather on Telegram, send /newbot, and paste the token it gives you.",
             None, "Open @BotFather", "https://t.me/BotFather"),
            ("telegram_chat_id", "Telegram Chat ID",
             "Message @userinfobot on Telegram -- it instantly replies with your numeric ID.",
             None, "Open @userinfobot", "https://t.me/userinfobot"),
            ("youtube_client_secrets", "YouTube client_secrets.json path",
             "In Google Cloud Console: create an OAuth Client ID (type 'Desktop app'), then download its JSON.",
             "open", "Open Google Cloud Console", "https://console.cloud.google.com/apis/credentials"),
            ("youtube_credentials_file", "YouTube credentials file path",
             "Just pick where to save this file. It's created automatically the first time you upload "
             "(a one-time Google login window will pop up).",
             "save", None, None),
        ]

        row = 0
        for key, label, hint, browse_mode, help_text, help_url in fields:
            top_pad = 12 if row == 0 else 10
            tk.Label(self, text=label, bg=colors["bg"], fg=colors["fg"], anchor="w",
                     font=("Segoe UI", 9, "bold")).grid(
                row=row, column=0, columnspan=3, sticky="w", padx=10, pady=(top_pad, 0)
            )
            row += 1
            tk.Label(self, text=hint, bg=colors["bg"], fg=colors["muted"], anchor="w",
                     wraplength=430, justify="left", font=("Segoe UI", 8)).grid(
                row=row, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 3)
            )
            row += 1

            var = tk.StringVar(value=cfg.get(key, ""))
            entry = tk.Entry(self, textvariable=var, width=42, bg=colors["entry_bg"], fg=colors["fg"],
                              insertbackground=colors["fg"], relief="flat")
            entry.grid(row=row, column=0, columnspan=2, sticky="we", padx=(10, 4), pady=(0, 4))
            self.vars[key] = var

            col = 2
            if browse_mode is not None:
                tk.Button(self, text="Browse...", bg=colors["entry_bg"], fg=colors["fg"], relief="flat",
                          padx=8, command=lambda v=var, m=browse_mode: self._browse(v, m)
                          ).grid(row=row, column=col, sticky="w", padx=4, pady=(0, 4))
                col += 1
            if help_url is not None:
                tk.Button(self, text=help_text, bg=colors["accent"], fg="white", relief="flat", padx=8,
                          command=lambda u=help_url: webbrowser.open(u)
                          ).grid(row=row, column=col, sticky="w", padx=4, pady=(0, 4))
            row += 1

        btn_frame = tk.Frame(self, bg=colors["bg"])
        btn_frame.grid(row=row, column=0, columnspan=4, pady=14)
        tk.Button(btn_frame, text="Save", command=self.save, bg=colors["accent"], fg="white",
                  relief="flat", padx=16).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Cancel", command=self.destroy, bg=colors["entry_bg"], fg=colors["fg"],
                  relief="flat", padx=16).pack(side="left", padx=6)

    def _browse(self, var, mode):
        if mode == "open":
            path = filedialog.askopenfilename(title="Select file", filetypes=[("JSON files", "*.json"),
                                                                                ("All files", "*.*")])
        else:  # "save"
            path = filedialog.asksaveasfilename(title="Choose where to save this file",
                                                 defaultextension=".json",
                                                 filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if path:
            var.set(path)

    def save(self):
        for key, var in self.vars.items():
            self.cfg[key] = var.get().strip()
        save_config(self.cfg)
        self.on_save()
        self.destroy()


class UploadManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bandwidth-Aware Universal Upload Manager")
        self.root.geometry("780x600")
        self.cfg = load_config()

        self.gui_queue = queue.Queue()
        self.upload_queue = []  # list of dicts: file, destination, bwlimit, status
        self.log_lines = []     # kept so the log survives a theme rebuild
        self.worker_thread = None

        self._refresh_colors()
        self._build_style()
        self._build_widgets()
        self.root.after(100, self._poll_gui_queue)

    # ---------------- Theme handling ----------------
    def _refresh_colors(self):
        theme = THEMES.get(self.cfg.get("theme", "Dark"), THEMES["Dark"])
        self.colors = dict(theme)
        self.colors["accent"] = ACCENTS.get(self.cfg.get("accent", "Blue"), ACCENTS["Blue"])
        self.root.configure(bg=self.colors["bg"])

    def _on_theme_change(self, *_):
        self.cfg["theme"] = self.theme_var.get()
        self.cfg["accent"] = self.accent_var.get()
        save_config(self.cfg)

        # Snapshot current queue state (widgets are about to be destroyed).
        current_file = self.file_var.get()
        current_dest = self.dest_var.get()
        current_bw = self.bw_var.get()

        for child in self.root.winfo_children():
            child.destroy()

        self._refresh_colors()
        self._build_style()
        self._build_widgets()

        # Restore state.
        self.file_var.set(current_file)
        self.dest_var.set(current_dest)
        self.bw_var.set(current_bw)
        self._snap_bw(None)
        for item in self.upload_queue:
            bw_text = "Unlimited" if item["bwlimit"] == 0 else f"{item['bwlimit']} MB/s"
            self.tree.insert("", "end", values=(os.path.basename(item["file"]), item["destination"],
                                                 bw_text, item["status"]))
        if self.log_lines:
            self._log("".join(self.log_lines), remember=False)

    # ---------------- UI construction ----------------
    def _build_style(self):
        c = self.colors
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=c["entry_bg"], background=c["entry_bg"],
                         foreground=c["fg"], arrowcolor=c["fg"])
        style.map("TCombobox", fieldbackground=[("readonly", c["entry_bg"])],
                   foreground=[("readonly", c["fg"])])
        style.configure("Horizontal.TScale", background=c["bg"], troughcolor=c["entry_bg"])
        style.configure("Treeview", background=c["panel"], fieldbackground=c["panel"], foreground=c["fg"],
                         rowheight=24, borderwidth=0)
        style.configure("Treeview.Heading", background=c["entry_bg"], foreground=c["fg"], relief="flat")
        style.map("Treeview", background=[("selected", c["accent"])])

    def _build_widgets(self):
        c = self.colors
        pad = {"padx": 10, "pady": 6}

        # --- Appearance row (top-right, applies instantly) ---
        appearance = tk.Frame(self.root, bg=c["bg"])
        appearance.pack(fill="x", padx=10, pady=(8, 0))
        tk.Label(appearance, text="Theme:", bg=c["bg"], fg=c["fg"]).pack(side="left")
        self.theme_var = tk.StringVar(value=self.cfg.get("theme", "Dark"))
        theme_combo = ttk.Combobox(appearance, textvariable=self.theme_var, values=list(THEMES.keys()),
                                    state="readonly", width=8)
        theme_combo.pack(side="left", padx=(4, 14))
        theme_combo.bind("<<ComboboxSelected>>", self._on_theme_change)

        tk.Label(appearance, text="Accent:", bg=c["bg"], fg=c["fg"]).pack(side="left")
        self.accent_var = tk.StringVar(value=self.cfg.get("accent", "Blue"))
        accent_combo = ttk.Combobox(appearance, textvariable=self.accent_var, values=list(ACCENTS.keys()),
                                     state="readonly", width=8)
        accent_combo.pack(side="left", padx=4)
        accent_combo.bind("<<ComboboxSelected>>", self._on_theme_change)

        # --- File selection row ---
        file_frame = tk.Frame(self.root, bg=c["bg"])
        file_frame.pack(fill="x", **pad)

        tk.Label(file_frame, text="File:", bg=c["bg"], fg=c["fg"]).pack(side="left")
        self.file_var = tk.StringVar()
        drop_target = tk.Entry(file_frame, textvariable=self.file_var, bg=c["entry_bg"], fg=c["fg"],
                                insertbackground=c["fg"], relief="flat")
        drop_target.pack(side="left", fill="x", expand=True, padx=8)
        tk.Button(file_frame, text="Browse...", command=self.browse_file, bg=c["entry_bg"], fg=c["fg"],
                  relief="flat", padx=10).pack(side="left")

        if DND_AVAILABLE:
            drop_target.drop_target_register(DND_FILES)
            drop_target.dnd_bind("<<Drop>>", self._on_drop)
        else:
            tk.Label(self.root, text="(Drag-and-drop disabled: pip install tkinterdnd2 to enable it)",
                      bg=c["bg"], fg=c["muted"], font=("Segoe UI", 8)).pack(anchor="w", padx=10)

        # --- Destination + bandwidth row ---
        options_frame = tk.Frame(self.root, bg=c["bg"])
        options_frame.pack(fill="x", **pad)

        tk.Label(options_frame, text="Destination:", bg=c["bg"], fg=c["fg"]).grid(row=0, column=0, sticky="w")
        self.dest_var = tk.StringVar(value=DESTINATIONS[0])
        dest_combo = ttk.Combobox(options_frame, textvariable=self.dest_var, values=DESTINATIONS,
                                   state="readonly", width=28)
        dest_combo.grid(row=0, column=1, sticky="w", padx=8)

        tk.Button(options_frame, text="Settings", command=self.open_settings, bg=c["entry_bg"], fg=c["fg"],
                  relief="flat", padx=10).grid(row=0, column=2, padx=8)

        tk.Label(options_frame, text="Speed limit (MB/s, 0 = Unlimited):", bg=c["bg"], fg=c["fg"]).grid(
            row=1, column=0, sticky="w", pady=(10, 0))
        self.bw_var = tk.IntVar(value=2)
        self.bw_scale = ttk.Scale(options_frame, from_=0, to=10, orient="horizontal",
                                   variable=self.bw_var, command=self._snap_bw, length=220)
        self.bw_scale.grid(row=1, column=1, sticky="w", padx=8, pady=(10, 0))
        self.bw_label = tk.Label(options_frame, text="2 MB/s", bg=c["bg"], fg=c["accent"], width=12)
        self.bw_label.grid(row=1, column=2, sticky="w", pady=(10, 0))

        # --- Queue controls ---
        queue_btns = tk.Frame(self.root, bg=c["bg"])
        queue_btns.pack(fill="x", **pad)
        tk.Button(queue_btns, text="Add to Queue", command=self.add_to_queue, bg=c["accent"], fg="white",
                  relief="flat", padx=14).pack(side="left")
        tk.Button(queue_btns, text="Remove Selected", command=self.remove_selected, bg=c["entry_bg"], fg=c["fg"],
                  relief="flat", padx=14).pack(side="left", padx=8)
        self.start_btn = tk.Button(queue_btns, text="Start Queue", command=self.start_queue, bg=c["ok"],
                                    fg="white", relief="flat", padx=14)
        self.start_btn.pack(side="left")

        # --- Queue table ---
        table_frame = tk.Frame(self.root, bg=c["bg"])
        table_frame.pack(fill="both", expand=False, padx=10, pady=(0, 6))
        columns = ("file", "destination", "bwlimit", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=6)
        for col, text, width in [("file", "File", 300), ("destination", "Destination", 180),
                                   ("bwlimit", "Limit", 80), ("status", "Status", 140)]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)

        # --- Log panel ---
        tk.Label(self.root, text="Log:", bg=c["bg"], fg=c["fg"]).pack(anchor="w", padx=10)
        self.log = scrolledtext.ScrolledText(self.root, bg=c["panel"], fg=c["fg"], insertbackground=c["fg"],
                                              relief="flat", height=12, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log.configure(state="disabled")

    # ---------------- Event handlers ----------------
    def _snap_bw(self, _value):
        val = int(round(self.bw_var.get()))
        self.bw_var.set(val)
        self.bw_label.config(text="Unlimited" if val == 0 else f"{val} MB/s")

    def _on_drop(self, event):
        path = event.data.strip("{}")  # tkinterdnd2 wraps paths with spaces in {}
        self.file_var.set(path)

    def browse_file(self):
        path = filedialog.askopenfilename(title="Select a file to upload")
        if path:
            self.file_var.set(path)

    def open_settings(self):
        SettingsDialog(self.root, self.cfg, self.colors, on_save=lambda: self._log("Settings saved.\n"))

    def add_to_queue(self):
        file_path = self.file_var.get().strip()
        if not file_path:
            messagebox.showwarning("No file", "Choose a file first.")
            return
        if not os.path.isfile(file_path):
            messagebox.showerror("File not found", f"'{file_path}' does not exist.")
            return

        item = {
            "file": file_path,
            "destination": self.dest_var.get(),
            "bwlimit": int(self.bw_var.get()),
            "status": "Queued",
        }
        self.upload_queue.append(item)
        bw_text = "Unlimited" if item["bwlimit"] == 0 else f"{item['bwlimit']} MB/s"
        self.tree.insert("", "end", values=(os.path.basename(file_path), item["destination"],
                                             bw_text, item["status"]))
        self.file_var.set("")

    def remove_selected(self):
        selected = self.tree.selection()
        for iid in selected:
            idx = self.tree.index(iid)
            self.tree.delete(iid)
            del self.upload_queue[idx]

    def start_queue(self):
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("Already running", "The queue is already being processed.")
            return
        if not self.upload_queue:
            messagebox.showinfo("Empty queue", "Add at least one file to the queue first.")
            return
        self.start_btn.config(state="disabled")
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()

    # ---------------- Background worker ----------------
    def _process_queue(self):
        for row_index, item in enumerate(self.upload_queue):
            if item["status"] != "Queued":
                continue
            self.gui_queue.put(("status", row_index, "Uploading..."))

            try:
                cmd, warning = build_command(item["destination"], item["file"], item["bwlimit"], self.cfg)
            except ValueError as e:
                self.gui_queue.put(("status", row_index, "Failed"))
                self.gui_queue.put(("log", f"[SKIPPED] {item['file']}: {e}\n"))
                continue

            self.gui_queue.put(("log", f"\n$ {' '.join(cmd)}\n"))
            if warning:
                self.gui_queue.put(("log", f"[WARNING] {warning}\n"))

            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1, creationflags=CREATE_NO_WINDOW,
                )
                for line in proc.stdout:
                    self.gui_queue.put(("log", line))
                proc.wait()

                if proc.returncode == 0:
                    self.gui_queue.put(("status", row_index, "Done"))
                    self.gui_queue.put(("log", f"[OK] Finished: {item['file']}\n"))
                else:
                    self.gui_queue.put(("status", row_index, "Failed"))
                    self.gui_queue.put(("log", f"[FAILED] Exit code {proc.returncode}: {item['file']}\n"))
            except FileNotFoundError:
                self.gui_queue.put(("status", row_index, "Failed"))
                tool = cmd[0]
                self.gui_queue.put(("log", f"[FAILED] '{tool}' was not found. Is it installed and on PATH?\n"))
            except Exception as e:
                self.gui_queue.put(("status", row_index, "Failed"))
                self.gui_queue.put(("log", f"[FAILED] {item['file']}: {e}\n"))

        self.gui_queue.put(("done", None, None))

    def _poll_gui_queue(self):
        try:
            while True:
                kind, a, b = self.gui_queue.get_nowait()
                if kind == "log":
                    self._log(a)
                elif kind == "status":
                    row_iid = self.tree.get_children()[a]
                    values = list(self.tree.item(row_iid, "values"))
                    values[3] = b
                    self.tree.item(row_iid, values=values)
                    self.upload_queue[a]["status"] = b
                elif kind == "done":
                    self.start_btn.config(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_gui_queue)

    def _log(self, text, remember=True):
        if remember:
            self.log_lines.append(text)
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")


def main():
    root = TkinterDnD.Tk() if DND_AVAILABLE else tk.Tk()
    UploadManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
