"""Admin-only Software Update Manager view."""

import customtkinter as ctk
import logging
import threading
from pathlib import Path
from typing import Optional

from src.config import APP_VERSION
from src.services.update_service import UpdateService

logger = logging.getLogger(__name__)


class UpdateManagerView(ctk.CTkFrame):
    """Desktop panel for checking and installing MediStock AI updates."""

    def __init__(self, parent, user_role: str):
        super().__init__(parent, fg_color="transparent")
        self.user_role = (user_role or "").lower()
        self.service = UpdateService()
        self._manifest: Optional[dict] = None
        self._installer_path: Optional[Path] = None
        self._create_widgets()

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="#0f1d37", corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(header, text="Software Updates", font=("Segoe UI", 20, "bold"), text_color="#6ee7ff").grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 2)
        )
        ctk.CTkLabel(
            header,
            text=f"Current version:  {APP_VERSION}   •   Admin-only",
            font=("Segoe UI", 13),
            text_color="#8fa2c9",
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))

        if self.user_role not in {"administrator", "admin"}:
            ctk.CTkLabel(
                header,
                text="Only administrators can manage software updates.",
                text_color="#fca5a5",
                font=("Segoe UI", 12),
            ).grid(row=2, column=0, sticky="w", padx=14, pady=(0, 10))
            return

        # Body
        body = ctk.CTkFrame(self, fg_color="#0f1d37", corner_radius=12)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        # Status banner
        self.status_frame = ctk.CTkFrame(body, fg_color="#091426", corner_radius=8)
        self.status_frame.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Press 'Check for Updates' to look for the latest version.",
            text_color="#93c5fd",
            font=("Segoe UI", 13),
            wraplength=700,
            justify="left",
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=12, pady=10)

        # Progress bar (hidden until download starts)
        self.progress_bar = ctk.CTkProgressBar(body, width=600)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 6))
        self.progress_bar.grid_remove()

        self.progress_label = ctk.CTkLabel(body, text="", text_color="#fbbf24", font=("Segoe UI", 11))
        self.progress_label.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 6))
        self.progress_label.grid_remove()

        # Release notes
        notes_label_frame = ctk.CTkFrame(body, fg_color="transparent")
        notes_label_frame.grid(row=3, column=0, sticky="ew", padx=14, pady=(8, 2))
        ctk.CTkLabel(notes_label_frame, text="Release notes", font=("Segoe UI", 13, "bold"), text_color="#dbeafe").pack(anchor="w")

        self.notes_box = ctk.CTkTextbox(body, height=180, fg_color="#091426", text_color="#94a3b8", font=("Segoe UI", 12))
        self.notes_box.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 10))
        self.notes_box.insert("end", "Release notes will appear here after you check for updates.")
        self.notes_box.configure(state="disabled")

        # Action buttons
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.grid(row=5, column=0, sticky="ew", padx=14, pady=(4, 14))
        btn_row.grid_columnconfigure(3, weight=1)

        self.check_button = ctk.CTkButton(
            btn_row, text="Check for Updates", width=180, command=self._check_for_update
        )
        self.check_button.grid(row=0, column=0, padx=(0, 8))

        self.download_button = ctk.CTkButton(
            btn_row,
            text="Download Update",
            width=180,
            fg_color="#065f46",
            hover_color="#047857",
            state="disabled",
            command=self._download_update,
        )
        self.download_button.grid(row=0, column=1, padx=(0, 8))

        self.install_button = ctk.CTkButton(
            btn_row,
            text="Install Now",
            width=180,
            fg_color="#1d4ed8",
            hover_color="#1e40af",
            state="disabled",
            command=self._install_update,
        )
        self.install_button.grid(row=0, column=2, padx=(0, 8))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _check_for_update(self):
        self._set_status("Checking for updates...", "#fbbf24")
        self.check_button.configure(state="disabled")

        def _worker():
            available, manifest, error = self.service.check_for_update()
            self.after(0, lambda: self._on_check_complete(available, manifest, error))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_check_complete(self, available: bool, manifest, error: str):
        self.check_button.configure(state="normal")
        if error and not manifest:
            self._set_status(f"Update check failed: {error}", "#fca5a5")
            return

        if not available:
            version = manifest.get("version", "?") if manifest else APP_VERSION
            self._set_status(
                f"You are on the latest version ({APP_VERSION}).  No update needed.",
                "#86efac",
            )
            self._update_notes("You have the latest version installed.\n\nNo update is available at this time.")
            return

        self._manifest = manifest
        latest = manifest.get("version", "?")
        self._set_status(
            f"New version available:  {latest}  (you have {APP_VERSION})  —  click Download Update.",
            "#fcd34d",
        )
        self._update_notes(self.service.get_release_notes(manifest))
        self.download_button.configure(state="normal")

    def _download_update(self):
        if not self._manifest:
            return
        self._set_status("Downloading update...", "#fbbf24")
        self.download_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_bar.grid()
        self.progress_label.configure(text="Starting download...")
        self.progress_label.grid()

        def _progress(downloaded: int, total: int):
            if total > 0:
                pct = downloaded / total
                mb_done = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                self.after(0, lambda: self._update_progress(pct, f"{mb_done:.1f} MB / {mb_total:.1f} MB"))
            else:
                mb_done = downloaded / (1024 * 1024)
                self.after(0, lambda: self._update_progress(0, f"{mb_done:.1f} MB downloaded..."))

        def _complete(success: bool, message: str, path):
            self.after(0, lambda: self._on_download_complete(success, message, path))

        self.service.download_update_async(self._manifest, on_progress=_progress, on_complete=_complete)

    def _update_progress(self, fraction: float, label: str):
        self.progress_bar.set(fraction)
        self.progress_label.configure(text=label)

    def _on_download_complete(self, success: bool, message: str, path):
        self.progress_bar.grid_remove()
        self.progress_label.grid_remove()
        if success:
            self._installer_path = path
            self._set_status(
                f"Download complete.  Click 'Install Now' to run the installer.",
                "#86efac",
            )
            self.install_button.configure(state="normal")
        else:
            self._set_status(f"Download failed: {message}", "#fca5a5")
            self.download_button.configure(state="normal")

    def _install_update(self):
        if not self._installer_path:
            return
        success, message = self.service.launch_installer(self._installer_path)
        if success:
            self._set_status(
                "Installer launched.  The app will close when you proceed with installation.",
                "#86efac",
            )
            self.install_button.configure(state="disabled")
        else:
            self._set_status(f"Could not launch installer: {message}", "#fca5a5")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, text: str, color: str = "#93c5fd"):
        self.status_label.configure(text=text, text_color=color)

    def _update_notes(self, text: str):
        self.notes_box.configure(state="normal")
        self.notes_box.delete("1.0", "end")
        self.notes_box.insert("end", text)
        self.notes_box.configure(state="disabled")
