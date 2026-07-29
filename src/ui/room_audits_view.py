"""
Room Audits View
UI for listing and viewing room audits
"""

import customtkinter as ctk
import logging
from datetime import datetime, date
from src.services.audit_service import AuditService
from src.services.room_service import ClinicalRoomService
from src.ui.room_audit_dialog import RoomAuditDialog
from src.models.models import RoomAudit
from src.ui.list_style_helpers import make_badge

logger = logging.getLogger(__name__)


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


class AuditDetailsDialog(ctk.CTkToplevel):
    """Dialog to display detailed audit results"""

    def __init__(self, parent, audit: RoomAudit, items: list):
        super().__init__(parent)
        self.title(f"Audit Details #{audit.id}")
        self.geometry("1200x820")
        self.minsize(1050, 700)
        self.resizable(True, True)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._maximize_window()

        self.audit = audit
        self.items = items
        self._setup_ui()

    def _maximize_window(self):
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                logger.warning("Unable to maximize audit details dialog window.")

    def _setup_ui(self):
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text=f"Audit #{self.audit.id}", font=("Segoe UI", 19, "bold")).pack(anchor="w", pady=(0, 10))

        info_text = (
            f"Room ID: {self.audit.room_id} | "
            f"Auditor ID: {self.audit.audited_by_user_id} | "
            f"Date: {self.audit.audit_date} | "
            f"Status: {self.audit.status}"
        )
        ctk.CTkLabel(main_frame, text=info_text, font=("Segoe UI", 14)).pack(anchor="w", pady=5)

        summary_text = (
            f"Items checked: {self.audit.total_items_checked or 0} | "
            f"Missing: {self.audit.missing_items_count or 0} | "
            f"Expired: {self.audit.expired_items_count or 0} | "
            f"Discrepancies: {self.audit.quantity_discrepancies_count or 0}"
        )
        ctk.CTkLabel(main_frame, text=summary_text, font=("Segoe UI", 14), text_color="gray").pack(anchor="w", pady=5)

        if self.audit.notes:
            ctk.CTkLabel(main_frame, text=f"Notes: {self.audit.notes}", font=("Segoe UI", 14), text_color="gray").pack(anchor="w", pady=(0, 10))

        headers = ["Item ID", "Expected", "Actual", "Discrepancy", "Expired", "Missing", "Notes"]
        widths = [100, 90, 90, 100, 70, 70, 240]

        header_row = ctk.CTkFrame(main_frame, fg_color="gray20", height=35)
        header_row.pack(fill="x", padx=5, pady=5)
        header_row.pack_propagate(False)
        for text, width in zip(headers, widths):
            ctk.CTkLabel(header_row, text=text, font=("Segoe UI", 12, "bold"), width=width).pack(side="left", padx=3)

        for item in self.items:
            row = ctk.CTkFrame(main_frame, fg_color="#111b2e", height=35)
            row.pack(fill="x", padx=5, pady=2)
            row.pack_propagate(False)

            columns = [
                str(item.item_id),
                str(item.expected_quantity or ""),
                str(item.actual_quantity or ""),
                str(item.quantity_discrepancy or ""),
                "Yes" if item.is_expired else "No",
                "Yes" if item.is_missing else "No",
                item.notes or "",
            ]

            for idx, (text, width) in enumerate(zip(columns, widths)):
                if idx in (4, 5):
                    make_badge(row, text, "#0f766e" if text == "No" else "#7c2d12", "#d1fae5" if text == "No" else "#fde68a", width).pack(side="left", padx=3)
                else:
                    ctk.CTkLabel(row, text=text, width=width, font=("Segoe UI", 12)).pack(side="left", padx=3)

    def _close(self):
        self.destroy()


class RoomAuditsView(ctk.CTkFrame):
    """Frame for managing room audits"""

    def __init__(self, parent, current_user_id: int, current_user_role: str = ""):
        super().__init__(parent)
        self.audit_service = AuditService()
        self.room_service = ClinicalRoomService()
        self.current_user_id = current_user_id
        self.is_admin = (current_user_role or "").lower() == "administrator"
        self.audits = []

        self._setup_ui()
        self._load_audits()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        title = ctk.CTkLabel(top_frame, text="Room Audits", font=("Segoe UI", 19, "bold"))
        title.pack(side="left", padx=5)

        ctk.CTkButton(top_frame, text="New Audit", width=120, command=self._new_audit).pack(side="right", padx=5)
        ctk.CTkButton(top_frame, text="Refresh", width=100, fg_color="gray", command=self._load_audits).pack(side="right", padx=5)

        self.status_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 14), text_color="gray")
        self.status_label.pack(anchor="w", padx=14, pady=(0, 8))

        self.audits_frame = ctk.CTkScrollableFrame(self, width=1100, height=520)
        self.audits_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._render_header()

    def _render_header(self):
        header = ctk.CTkFrame(self.audits_frame, fg_color="gray20", height=35)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)

        columns = ["Audit ID", "Room", "Date", "Auditor", "Status", "Items", "Missing", "Expired", "Discrepancies", "Actions"]
        widths = [80, 170, 90, 80, 90, 70, 70, 70, 100, 360]

        for text, width in zip(columns, widths):
            ctk.CTkLabel(header, text=text, width=width, font=("Segoe UI", 12, "bold")).pack(side="left", padx=3)

    def _load_audits(self):
        for widget in self.audits_frame.winfo_children()[1:]:
            widget.destroy()

        self.audits = self.audit_service.get_audits()
        if not self.audits:
            ctk.CTkLabel(self.audits_frame, text="No audits recorded yet.", font=("Segoe UI", 14), text_color="gray").pack(pady=30)
            return

        for audit in self.audits:
            self._add_audit_row(audit)

    def _add_audit_row(self, audit: RoomAudit):
        row = ctk.CTkFrame(self.audits_frame, fg_color="#111b2e", height=38)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)

        room = self.room_service.get_room_by_id(audit.room_id)
        room_name = room.room_name if room else f"Room {audit.room_id}"

        columns = [
            str(audit.id),
            f"🏥 {room_name}",
            str(audit.audit_date or ""),
            str(audit.audited_by_user_id),
            audit.status,
            str(audit.total_items_checked or ""),
            str(audit.missing_items_count or ""),
            str(audit.expired_items_count or ""),
            str(audit.quantity_discrepancies_count or ""),
        ]
        widths = [80, 180, 90, 80, 90, 70, 70, 70, 100]

        for idx, (text, width) in enumerate(zip(columns, widths)):
            if idx == 4:
                status_lower = (text or "").lower()
                bg = "#0f766e" if status_lower in {"complete", "completed"} else "#6d28d9"
                fg = "#d1fae5" if status_lower in {"complete", "completed"} else "#e9d5ff"
                make_badge(row, text.title(), bg, fg, width).pack(side="left", padx=3)
            elif idx in (5, 6, 7, 8):
                make_badge(row, text or "0", "#1e293b", "#cbd5e1", width).pack(side="left", padx=3)
            else:
                ctk.CTkLabel(row, text=text, width=width, font=("Segoe UI", 12)).pack(side="left", padx=3)

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="left", padx=3)

        ctk.CTkButton(actions, text="👁", width=28, height=24, fg_color="#1f6aa5", command=lambda a=audit: self._view_audit(a)).pack(side="left", padx=2)
        ctk.CTkButton(actions, text="✓", width=28, height=24, fg_color="green", command=lambda a=audit: self._complete_audit(a)).pack(side="left", padx=2)
        ctk.CTkButton(actions, text="↻", width=28, height=24, fg_color="#1d4ed8", command=lambda a=audit: self._rerun_audit(a)).pack(side="left", padx=2)
        ctk.CTkButton(
            actions,
            text="🗑",
            width=28,
            fg_color="red",
            state="normal" if self.is_admin else "disabled",
            command=lambda a=audit: self._delete_audit(a),
        ).pack(
            side="left", padx=3
        )

    def _new_audit(self):
        RoomAuditDialog(self, self.current_user_id, on_save=self._load_audits)

    def _view_audit(self, audit: RoomAudit):
        items = self.audit_service.get_audit_items(audit.id)
        AuditDetailsDialog(self, audit, items)

    def _complete_audit(self, audit: RoomAudit):
        success, message = self.audit_service.complete_audit(audit.id)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_audits()
        logger.info(message)

    def _prompt_admin_password(self):
        dialog = AdminPasswordDialog(self)
        dialog.wait_window()
        return dialog.result

    def _delete_audit(self, audit: RoomAudit):
        if not self.is_admin:
            self.status_label.configure(text="Only administrators can delete transaction records.", text_color="red")
            return

        password = self._prompt_admin_password()
        if password is None:
            self.status_label.configure(text="Delete audit cancelled.", text_color="gray")
            return
        success, message = self.audit_service.delete_audit(audit.id, password)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_audits()

    def _rerun_audit(self, audit: RoomAudit):
        password = self._prompt_admin_password()
        if password is None:
            self.status_label.configure(text="Re-run audit cancelled.", text_color="gray")
            return

        verified, message = self.audit_service.verify_admin_password(password)
        if not verified:
            self.status_label.configure(text=message, text_color="red")
            return

        room = self.room_service.get_room_by_id(audit.room_id)
        if not room:
            self.status_label.configure(text="Room not found for selected audit.", text_color="red")
            return

        self.status_label.configure(text="Administrator verified. Starting re-run audit.", text_color="green")
        RoomAuditDialog(self, self.current_user_id, room=room, on_save=self._load_audits)
