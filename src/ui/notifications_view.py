"""
Notifications View
Displays operational notifications and alerts.
"""

import customtkinter as ctk

from src.services.notifications_service import NotificationsService


class NotificationsView(ctk.CTkFrame):
    """Frame for notification center."""

    def __init__(self, parent):
        super().__init__(parent)
        self.notifications_service = NotificationsService()
        self.notifications = []
        self._setup_ui()
        self._load_notifications()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="Notifications Center", font=("Arial", 16, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(top_frame, text="Refresh", width=100, fg_color="gray", command=self._load_notifications).pack(
            side="right", padx=5
        )

        self.summary_label = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color="gray")
        self.summary_label.pack(anchor="w", padx=14, pady=(0, 8))

        self.notifications_frame = ctk.CTkScrollableFrame(self, width=1120, height=540)
        self.notifications_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._render_header()

    def _render_header(self):
        header = ctk.CTkFrame(self.notifications_frame, fg_color="gray20", height=35)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)

        columns = [("Severity", 90), ("Type", 120), ("Title", 290), ("Message", 420), ("Reference", 120)]
        for text, width in columns:
            ctk.CTkLabel(header, text=text, width=width, font=("Arial", 10, "bold")).pack(side="left", padx=3)

    def _load_notifications(self):
        for widget in self.notifications_frame.winfo_children()[1:]:
            widget.destroy()

        self.notifications = self.notifications_service.get_notifications()
        critical = len([row for row in self.notifications if row["severity"] == "critical"])
        warning = len([row for row in self.notifications if row["severity"] == "warning"])
        info = len([row for row in self.notifications if row["severity"] == "info"])
        self.summary_label.configure(
            text=f"Critical: {critical} | Warning: {warning} | Info: {info} | Total: {len(self.notifications)}"
        )

        if not self.notifications:
            ctk.CTkLabel(self.notifications_frame, text="No active notifications.", text_color="gray").pack(pady=30)
            return

        for index, notification in enumerate(self.notifications):
            self._add_notification_row(notification, index % 2 == 0)

    def _add_notification_row(self, notification: dict, alternate: bool):
        bg_color = "gray15" if alternate else "gray10"
        row = ctk.CTkFrame(self.notifications_frame, fg_color=bg_color, height=38)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)

        severity = notification.get("severity", "info")
        severity_color = {"critical": "red", "warning": "orange", "info": "lightblue"}.get(severity, "gray")
        columns = [
            (severity.title(), 90, severity_color),
            (notification.get("type", "-").replace("_", " ").title(), 120, None),
            (notification.get("title", "-")[:46], 290, None),
            (notification.get("message", "-")[:80], 420, None),
            (notification.get("reference", "-")[:20], 120, None),
        ]
        for text, width, text_color in columns:
            ctk.CTkLabel(row, text=text, width=width, text_color=text_color).pack(side="left", padx=3)
