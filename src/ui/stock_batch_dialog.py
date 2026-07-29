"""
Stock batch dialog.
Dialog for creating and editing stock batches.
"""

import customtkinter as ctk
import logging
from datetime import datetime
from typing import Optional

from src.models.models import StockBatch
from src.services.inventory_service import InventoryService
from src.services.room_service import ClinicalRoomService
from src.ui.voice_typing_mixin import VoiceTypingMixin

logger = logging.getLogger(__name__)


class StockBatchDialog(VoiceTypingMixin, ctk.CTkToplevel):
    """Dialog for creating or editing a stock batch."""

    STATUS_OPTIONS = ["Active", "Opened", "Expired", "Quarantined", "Used Up", "Disposed"]

    def __init__(
        self,
        parent,
        batch: Optional[StockBatch] = None,
        on_save: Optional[callable] = None,
        on_delete: Optional[callable] = None,
    ):
        super().__init__(parent)
        self.title("Add Stock Batch" if not batch else "Edit Stock Batch")
        self.geometry("620x760")
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)

        self.batch = batch
        self.on_save = on_save
        self.on_delete = on_delete
        self.inventory_service = InventoryService()
        self.room_service = ClinicalRoomService()
        self.fields = {}
        self.item_options = self._build_item_options()
        self.room_options = self._build_room_options()
        self._initialize_voice_typing()

        self._setup_ui()
        if batch:
            self._load_batch(batch)

    def _setup_ui(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        title_text = "Create a new stock batch" if not self.batch else f"Edit stock batch: {self.batch.batch_number}"
        ctk.CTkLabel(frame, text=title_text, font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 10))

        batch_id_text = f"Batch ID: {self.batch.id}" if self.batch and self.batch.id else "Batch ID: assigned after save"
        ctk.CTkLabel(frame, text=batch_id_text, font=("Arial", 11), text_color="gray").pack(anchor="w", pady=(0, 10))

        form_frame = ctk.CTkScrollableFrame(frame)
        form_frame.pack(fill="both", expand=True)

        self.fields["item"] = self._create_combo_field(form_frame, "Product *", self.item_options or [""])
        self.fields["room"] = self._create_combo_field(form_frame, "Room", self.room_options or [""])
        self.fields["qr_code"] = self._create_entry_field(form_frame, "Batch QR Code")
        self.fields["batch_number"] = self._create_entry_field(form_frame, "Batch Number *")
        self.fields["expiry_date"] = self._create_entry_field(form_frame, "Expiry Date (YYYY-MM-DD)")
        self.fields["quantity_available"] = self._create_entry_field(form_frame, "Quantity Available *")
        self.fields["date_received"] = self._create_entry_field(form_frame, "Date Received (YYYY-MM-DD)")
        self.fields["opened_date"] = self._create_entry_field(form_frame, "Opened Date (YYYY-MM-DD)")
        self.fields["expiry_period_after_opening"] = self._create_entry_field(form_frame, "Expiry Period After Opening (days)")
        self.fields["storage_location"] = self._create_entry_field(form_frame, "Storage Location")
        self.fields["status"] = self._create_combo_field(form_frame, "Status *", self.STATUS_OPTIONS)

        self.status_label = ctk.CTkLabel(frame, text="", font=("Arial", 10), text_color="red")
        self.status_label.pack(anchor="w", pady=(8, 6))

        button_frame = ctk.CTkFrame(frame)
        button_frame.pack(fill="x", pady=(8, 0))

        ctk.CTkButton(button_frame, text="Save Batch", width=130, command=self._save_batch).pack(side="left", padx=5)
        if self.batch and self.batch.id:
            ctk.CTkButton(
                button_frame,
                text="Delete Batch",
                width=130,
                fg_color="red",
                command=self._delete_batch,
            ).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", width=130, fg_color="gray", command=self._close).pack(side="left", padx=5)

        if not self.item_options:
            self._set_status("Create an inventory item before adding stock batches.", success=False)

    def _create_entry_field(self, parent, label: str):
        return self._create_voice_field(parent, label, multiline=False, width=400)

    def _create_combo_field(self, parent, label: str, values):
        field_frame = ctk.CTkFrame(parent)
        field_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(field_frame, text=label, font=("Arial", 11, "bold")).pack(anchor="w")
        combo = ctk.CTkComboBox(field_frame, values=values, state="readonly")
        combo.pack(fill="x", pady=5)
        combo.set(values[0] if values else "")
        return combo

    def _build_item_options(self):
        items = self.inventory_service.get_all_items()
        return [f"{item.id} - {item.item_name}" for item in items if item.id]

    def _build_room_options(self):
        rooms = self.room_service.get_all_rooms()
        return ["Not assigned"] + [f"{room.id} - {room.room_name}" for room in rooms if room.id]

    def _load_batch(self, batch: StockBatch):
        item_value = self._find_option_with_prefix(self.item_options, batch.item_id)
        if item_value:
            self.fields["item"].set(item_value)

        room_value = self._find_option_with_prefix(self.room_options, batch.room_id)
        self.fields["room"].set(room_value or "Not assigned")
        self.fields["qr_code"].insert(0, batch.qr_code or "")
        self.fields["batch_number"].insert(0, batch.batch_number or "")
        if batch.expiry_date:
            self.fields["expiry_date"].insert(0, batch.expiry_date.isoformat())
        self.fields["quantity_available"].insert(0, str(batch.quantity_available))
        if batch.date_received:
            self.fields["date_received"].insert(0, batch.date_received.isoformat())
        if batch.opened_date:
            self.fields["opened_date"].insert(0, batch.opened_date.isoformat())
        if batch.expiry_period_after_opening is not None:
            self.fields["expiry_period_after_opening"].insert(0, str(batch.expiry_period_after_opening))
        self.fields["storage_location"].insert(0, batch.storage_location or "")
        self.fields["status"].set(batch.status or "Active")

    def _save_batch(self):
        try:
            item_id = self._parse_prefixed_id(self.fields["item"].get().strip())
            if not item_id:
                self._set_status("Product is required", success=False)
                return

            room_value = self.fields["room"].get().strip()
            room_id = None if room_value in {"", "Not assigned"} else self._parse_prefixed_id(room_value)

            quantity_value = self.fields["quantity_available"].get().strip()
            if not quantity_value:
                self._set_status("Quantity available is required", success=False)
                return
            quantity_available = int(quantity_value)
            if quantity_available < 0:
                self._set_status("Quantity available cannot be negative", success=False)
                return

            expiry_period_value = self.fields["expiry_period_after_opening"].get().strip()
            expiry_period_after_opening = int(expiry_period_value) if expiry_period_value else None
            if expiry_period_after_opening is not None and expiry_period_after_opening < 0:
                self._set_status("Expiry period after opening cannot be negative", success=False)
                return

            batch = self.batch or StockBatch()
            batch.item_id = item_id
            batch.room_id = room_id
            batch.qr_code = self.fields["qr_code"].get().strip() or None
            batch.batch_number = self.fields["batch_number"].get().strip()
            batch.expiry_date = self._parse_date_field(self.fields["expiry_date"].get().strip(), "Expiry date")
            batch.quantity_available = quantity_available
            batch.date_received = self._parse_date_field(self.fields["date_received"].get().strip(), "Date received")
            batch.opened_date = self._parse_date_field(self.fields["opened_date"].get().strip(), "Opened date")
            batch.expiry_period_after_opening = expiry_period_after_opening
            batch.storage_location = self.fields["storage_location"].get().strip() or None
            batch.status = self.fields["status"].get().strip() or "Active"

            self.batch = batch
            if self.on_save:
                self.on_save(self.batch)
            self._close()
        except ValueError as e:
            self._set_status(str(e), success=False)

    def _delete_batch(self):
        if not self.batch or not self.batch.id:
            self._set_status("Batch cannot be deleted before it is created.", success=False)
            return
        if self.on_delete:
            self.on_delete(self.batch)
        self._close()

    @staticmethod
    def _parse_prefixed_id(value: str) -> Optional[int]:
        if not value:
            return None
        prefix = value.split(" - ", 1)[0].strip()
        return int(prefix) if prefix.isdigit() else None

    @staticmethod
    def _find_option_with_prefix(options, identifier: Optional[int]) -> Optional[str]:
        if identifier is None:
            return None
        prefix = f"{identifier} - "
        return next((option for option in options if option.startswith(prefix)), None)

    @staticmethod
    def _parse_date_field(value: str, label: str):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"{label} must be in YYYY-MM-DD format")

    def _close(self):
        self.destroy()

    def _set_status(self, message: str, success: bool = True):
        self.status_label.configure(text=message, text_color="green" if success else "red")
        logger.info(message)
