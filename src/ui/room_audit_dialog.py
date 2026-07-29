"""
Room Audit Dialog
Dialog for recording a clinical room audit
"""

import customtkinter as ctk
import logging
from typing import Optional, List
from datetime import date, datetime
from src.services.room_service import ClinicalRoomService
from src.services.audit_service import AuditService
from src.models.models import ClinicalRoom, Item, RoomAudit, AuditItem

logger = logging.getLogger(__name__)


class RoomAuditDialog(ctk.CTkToplevel):
    """Dialog for starting and saving a room audit"""

    def __init__(
        self,
        parent,
        current_user_id: int,
        room: Optional[ClinicalRoom] = None,
        on_save: Optional[callable] = None,
    ):
        super().__init__(parent)
        self.title("New Room Audit")
        self.geometry("1200x850")
        self.minsize(1100, 760)
        self.resizable(True, True)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._maximize_window()

        self.current_user_id = current_user_id
        self.room = room
        self.on_save = on_save
        self.room_service = ClinicalRoomService()
        self.audit_service = AuditService()
        self.item_rows = []

        self._setup_ui()
        if self.room:
            self.room_dropdown.set(self.room.room_name)
            self._load_room_items(self.room)

    def _maximize_window(self):
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                logger.warning("Unable to maximize room audit dialog window.")

    def _setup_ui(self):
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text="Room Audit", font=("Arial", 16, "bold")).pack(anchor="w", pady=(0, 10))

        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", pady=10)

        room_names = [room.room_name for room in self.room_service.get_all_rooms()]
        ctk.CTkLabel(form_frame, text="Clinical Room:", font=("Arial", 11, "bold")).grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.room_dropdown = ctk.CTkComboBox(
            form_frame,
            values=room_names,
            state="readonly",
            command=self._on_room_selected,
        )
        self.room_dropdown.grid(row=0, column=1, sticky="ew", pady=5, padx=5)
        self.room_dropdown.configure(width=300)

        ctk.CTkLabel(form_frame, text="Audit Date (DD-MM-YYYY):", font=("Arial", 11, "bold")).grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.audit_date_entry = ctk.CTkEntry(form_frame)
        self.audit_date_entry.grid(row=1, column=1, sticky="ew", pady=5, padx=5)
        self.audit_date_entry.insert(0, date.today().strftime("%d-%m-%Y"))

        ctk.CTkLabel(form_frame, text="Auditor User ID:", font=("Arial", 11, "bold")).grid(row=2, column=0, sticky="w", pady=5, padx=5)
        self.auditor_entry = ctk.CTkEntry(form_frame)
        self.auditor_entry.grid(row=2, column=1, sticky="ew", pady=5, padx=5)
        self.auditor_entry.insert(0, str(self.current_user_id))

        ctk.CTkLabel(form_frame, text="Notes:", font=("Arial", 11, "bold")).grid(row=3, column=0, sticky="nw", pady=5, padx=5)
        self.notes_box = ctk.CTkTextbox(form_frame, height=80)
        self.notes_box.grid(row=3, column=1, sticky="ew", pady=5, padx=5)

        form_frame.grid_columnconfigure(1, weight=1)

        self.items_frame = ctk.CTkScrollableFrame(main_frame, height=430)
        self.items_frame.pack(fill="both", expand=True, pady=10)

        self._create_items_header()
        self._create_items_placeholder()

        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=10)

        ctk.CTkButton(button_frame, text="Save Audit", command=self._save_audit, width=140).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", fg_color="gray", command=self._close, width=140).pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(main_frame, text="Select a room to begin the audit.", font=("Arial", 11), text_color="gray")
        self.status_label.pack(anchor="w", pady=5)

    def _create_items_header(self):
        header = ctk.CTkFrame(self.items_frame, fg_color="gray20", height=35)
        header.pack(fill="x", padx=5, pady=2)
        header.pack_propagate(False)

        columns = [
            ("Item", 220),
            ("Barcode", 120),
            ("Expected", 80),
            ("Actual", 80),
            ("Discrepancy", 100),
            ("Expired", 70),
            ("Missing", 70),
            ("Notes", 180),
        ]

        for text, width in columns:
            ctk.CTkLabel(header, text=text, width=width, font=("Arial", 10, "bold")).pack(side="left", padx=3)

    def _create_items_placeholder(self):
        self.placeholder = ctk.CTkLabel(self.items_frame, text="No room selected.", font=("Arial", 11), text_color="gray")
        self.placeholder.pack(pady=40)

    def _on_room_selected(self, value=None):
        room_name = self.room_dropdown.get()
        room = next((room for room in self.room_service.get_all_rooms() if room.room_name == room_name), None)
        if room:
            self.room = room
            self._load_room_items(room)

    def _load_room_items(self, room: ClinicalRoom):
        for widget in self.items_frame.winfo_children():
            widget.destroy()
        self._create_items_header()
        self.item_rows = []

        items = self.room_service.get_items_in_room(room.room_name)
        if not items:
            ctk.CTkLabel(self.items_frame, text="No inventory items assigned to this room.", font=("Arial", 11), text_color="gray").pack(pady=40)
            return

        for item in items:
            self._add_item_row(item)

    def _add_item_row(self, item: Item):
        row = ctk.CTkFrame(self.items_frame, fg_color="gray15", height=40)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)

        self.item_rows.append((item, row))

        ctk.CTkLabel(row, text=item.item_name[:20], width=220).pack(side="left", padx=3)
        ctk.CTkLabel(row, text=item.barcode or "-", width=120).pack(side="left", padx=3)
        ctk.CTkLabel(row, text=str(item.current_quantity), width=80).pack(side="left", padx=3)

        actual_entry = ctk.CTkEntry(row, width=80)
        actual_entry.insert(0, str(item.current_quantity))
        actual_entry.pack(side="left", padx=3)

        discrepancy_label = ctk.CTkLabel(row, text="0", width=100)
        discrepancy_label.pack(side="left", padx=3)

        expired_checkbox = ctk.CTkCheckBox(row, text="", width=70)
        expired_checkbox.pack(side="left", padx=3)
        if item.expiry_date and item.expiry_date <= date.today():
            expired_checkbox.select()

        missing_checkbox = ctk.CTkCheckBox(row, text="", width=70)
        missing_checkbox.pack(side="left", padx=3)
        if item.current_quantity == 0:
            missing_checkbox.select()

        notes_entry = ctk.CTkEntry(row, width=180)
        notes_entry.pack(side="left", padx=3)

        actual_entry.bind(
            "<KeyRelease>",
            lambda e, expected=item.current_quantity, label=discrepancy_label: self._update_discrepancy(expected, e.widget.get(), label),
        )

        self.item_rows[-1] = {
            "item": item,
            "actual_entry": actual_entry,
            "discrepancy_label": discrepancy_label,
            "expired_checkbox": expired_checkbox,
            "missing_checkbox": missing_checkbox,
            "notes_entry": notes_entry,
        }

    def _update_discrepancy(self, expected_value: int, actual_text: str, label: ctk.CTkLabel):
        try:
            actual = int(actual_text) if actual_text.strip() else 0
            discrepancy = actual - expected_value
            label.configure(text=str(discrepancy))
        except ValueError:
            label.configure(text="?")

    def _save_audit(self):
        if not self.room:
            self._set_status("Select a room before saving the audit.", success=False)
            return

        audit_items: List[AuditItem] = []
        for row_data in self.item_rows:
            item = row_data["item"]
            actual_text = row_data["actual_entry"].get().strip()
            try:
                actual_quantity = int(actual_text) if actual_text else 0
            except ValueError:
                self._set_status(f"Invalid actual quantity for {item.item_name}", success=False)
                return

            expected_quantity = item.current_quantity
            quantity_discrepancy = actual_quantity - expected_quantity
            audit_items.append(
                AuditItem(
                    item_id=item.id,
                    expected_quantity=expected_quantity,
                    actual_quantity=actual_quantity,
                    quantity_discrepancy=quantity_discrepancy,
                    is_expired=bool(row_data["expired_checkbox"].get()),
                    is_missing=bool(row_data["missing_checkbox"].get()),
                    notes=row_data["notes_entry"].get().strip() or None,
                )
            )

        try:
            audit_date = self._parse_audit_date(self.audit_date_entry.get()) if self.audit_date_entry.get().strip() else date.today()
        except ValueError:
            self._set_status("Invalid audit date format (use DD-MM-YYYY).", success=False)
            return

        audit = RoomAudit(
            room_id=self.room.id,
            audit_date=audit_date,
            audit_time=datetime.now().strftime("%H:%M:%S"),
            audited_by_user_id=int(self.auditor_entry.get().strip()),
            status="completed",
            notes=self.notes_box.get("1.0", "end").strip() or None,
        )

        success, message, audit_id = self.audit_service.create_audit(audit, audit_items)
        self._set_status(message, success=success)

        if success:
            if self.on_save:
                self.on_save()
            self._close()

    def _set_status(self, message: str, success: bool = True):
        self.status_label.configure(text=message, text_color="green" if success else "red")
        logger.info(message)

    def _close(self):
        self.destroy()

    @staticmethod
    def _parse_audit_date(value: str):
        value = value.strip()
        for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        raise ValueError("Invalid audit date format")
