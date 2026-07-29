"""
Backup View
UI for creating and restoring database backups.
"""

import customtkinter as ctk
from pathlib import Path

from src.services.backup_service import BackupService


class AdminPasswordDialog(ctk.CTkToplevel):
    """Simple modal dialog to request admin password."""

    def __init__(self, parent, title: str = "Admin Password Required"):
        super().__init__(parent)
        self.title(title)
        self.geometry("420x180")
        self.resizable(False, False)
        self.grab_set()
        self.result = None

        ctk.CTkLabel(self, text="Enter administrator password to continue:", font=("Arial", 11)).pack(
            anchor="w", padx=16, pady=(18, 8)
        )
        self.password_entry = ctk.CTkEntry(self, show="*", width=360)
        self.password_entry.pack(padx=16, pady=6)
        self.password_entry.focus_set()

        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=16, pady=14)
        ctk.CTkButton(button_frame, text="Confirm", width=100, command=self._confirm).pack(side="left", padx=4)
        ctk.CTkButton(button_frame, text="Cancel", width=100, fg_color="gray", command=self._cancel).pack(
            side="left", padx=4
        )

    def _confirm(self):
        self.result = self.password_entry.get()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class BackupView(ctk.CTkFrame):
    """Frame for backup and restore operations."""

    def __init__(self, parent):
        super().__init__(parent)
        self.backup_service = BackupService()
        self.backups = []
        self.auto_backup_enabled_var = ctk.BooleanVar(value=False)
        self._setup_ui()
        self._load_auto_backup_settings()
        self._load_backups()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="Backup & Restore", font=("Arial", 16, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(top_frame, text="Create Backup", width=140, command=self._create_backup).pack(side="right", padx=5)
        ctk.CTkButton(top_frame, text="Refresh", width=100, fg_color="gray", command=self._load_backups).pack(side="right", padx=5)

        self.status_label = ctk.CTkLabel(
            self,
            text="Create a backup before major changes.",
            font=("Arial", 11),
            text_color="gray",
        )
        self.status_label.pack(anchor="w", padx=14, pady=(0, 8))

        settings_frame = ctk.CTkFrame(self)
        settings_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(settings_frame, text="Automatic Daily Backup", font=("Arial", 12, "bold")).pack(
            side="left", padx=8, pady=8
        )
        ctk.CTkCheckBox(
            settings_frame,
            text="Enabled",
            variable=self.auto_backup_enabled_var,
            font=("Arial", 11),
        ).pack(side="left", padx=8)
        ctk.CTkLabel(settings_frame, text="Time (HH:MM):", font=("Arial", 11)).pack(side="left", padx=(16, 4))
        self.auto_backup_time_entry = ctk.CTkEntry(settings_frame, width=80)
        self.auto_backup_time_entry.pack(side="left", padx=4)
        ctk.CTkButton(settings_frame, text="Save Schedule", width=120, command=self._save_auto_backup_settings).pack(
            side="left", padx=8
        )

        self.backups_frame = ctk.CTkScrollableFrame(self, width=1120, height=520)
        self.backups_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._render_header()

    def _render_header(self):
        header = ctk.CTkFrame(self.backups_frame, fg_color="gray20", height=35)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)

        columns = [("Backup File", 470), ("Modified", 170), ("Size", 110), ("Actions", 260)]
        for text, width in columns:
            ctk.CTkLabel(header, text=text, width=width, font=("Arial", 10, "bold")).pack(side="left", padx=3)

    def _create_backup(self):
        success, message, backup_path = self.backup_service.create_backup()
        self.status_label.configure(
            text=f"{message}: {backup_path.name}" if success and backup_path else message,
            text_color="green" if success else "red",
        )
        if success:
            self._load_backups()

    def _load_backups(self):
        for widget in self.backups_frame.winfo_children()[1:]:
            widget.destroy()

        self.backups = self.backup_service.list_backups()
        if not self.backups:
            ctk.CTkLabel(self.backups_frame, text="No backups found.", text_color="gray").pack(pady=25)
            return

        for idx, backup in enumerate(self.backups):
            self._add_backup_row(backup, idx % 2 == 0)

    def _load_auto_backup_settings(self):
        settings = self.backup_service.get_auto_backup_settings()
        self.auto_backup_enabled_var.set(bool(settings["enabled"]))
        self.auto_backup_time_entry.delete(0, "end")
        self.auto_backup_time_entry.insert(0, settings["schedule_time"])

    def _save_auto_backup_settings(self):
        success, message = self.backup_service.update_auto_backup_settings(
            enabled=self.auto_backup_enabled_var.get(),
            schedule_time=self.auto_backup_time_entry.get().strip(),
        )
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_auto_backup_settings()

    def _add_backup_row(self, backup_path: Path, alternate: bool):
        bg = "gray15" if alternate else "gray10"
        row = ctk.CTkFrame(self.backups_frame, fg_color=bg, height=35)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)

        modified = self._fmt_datetime(backup_path.stat().st_mtime)
        size_mb = backup_path.stat().st_size / (1024 * 1024)

        values = [
            (backup_path.name[:72], 470),
            (modified, 170),
            (f"{size_mb:.2f} MB", 110),
        ]
        for text, width in values:
            ctk.CTkLabel(row, text=text, width=width).pack(side="left", padx=3)

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="left", padx=3)

        ctk.CTkButton(
            actions,
            text="Restore",
            width=110,
            fg_color="orange",
            command=lambda p=backup_path: self._restore_backup(p),
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            actions,
            text="Delete",
            width=110,
            fg_color="red",
            command=lambda p=backup_path: self._delete_backup(p),
        ).pack(side="left", padx=3)

    def _restore_backup(self, backup_path: Path):
        success, message = self.backup_service.restore_backup(backup_path)
        status_message = message
        if success:
            status_message = f"{message}. Please restart the app to ensure all views use the restored data."
        self.status_label.configure(text=status_message, text_color="green" if success else "red")

    def _prompt_admin_password(self):
        dialog = AdminPasswordDialog(self)
        dialog.wait_window()
        return dialog.result

    def _delete_backup(self, backup_path: Path):
        password = self._prompt_admin_password()
        if password is None:
            self.status_label.configure(text="Delete backup cancelled.", text_color="gray")
            return

        success, message = self.backup_service.delete_backup(backup_path, password)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_backups()

    @staticmethod
    def _fmt_datetime(timestamp: float) -> str:
        import datetime

        return datetime.datetime.fromtimestamp(timestamp).strftime("%d-%m-%Y %H:%M")
