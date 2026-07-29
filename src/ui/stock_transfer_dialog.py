"""
Stock Transfer Dialog
Dialog for recording a stock transfer between rooms
"""

import customtkinter as ctk
import logging
from typing import Optional
from datetime import date, datetime
from src.services.transfer_service import TransferService
from src.services.room_service import ClinicalRoomService
from src.services.inventory_service import InventoryService
from src.services.time_sync_service import get_time_sync_service
from src.models.models import StockTransfer, Item, ClinicalRoom
from src.ui.action_confirmation_dialog import ActionConfirmationDialog
from src.ui.voice_typing_mixin import VoiceTypingMixin
from src.config import CLINICAL_SAFETY_CHECK_NOTICE

logger = logging.getLogger(__name__)


class StockTransferDialog(VoiceTypingMixin, ctk.CTkToplevel):
    """Dialog for creating or editing a stock transfer"""

    def __init__(
        self,
        parent,
        current_user_id: int,
        on_save: Optional[callable] = None,
    ):
        super().__init__(parent)
        self.title("Record Stock Transfer")
        self.geometry("700x620")
        self.resizable(False, False)
        self.grab_set()

        self.current_user_id = current_user_id
        self.on_save = on_save
        self.transfer_service = TransferService()
        self.room_service = ClinicalRoomService()
        self.inventory_service = InventoryService()
        self.time_sync_service = get_time_sync_service()
        self.fields = {}
        self._initialize_voice_typing()

        self._setup_ui()

    def _setup_ui(self):
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text="New Stock Transfer", font=("Arial", 16, "bold")).pack(anchor="w", pady=(0, 10))

        rooms = self.room_service.get_all_rooms()
        room_names = [room.room_name for room in rooms]

        self._create_combo_field(main_frame, "Item", self._get_item_options(), "item")
        self._create_combo_field(main_frame, "From Room", room_names, "from_room")
        self._create_combo_field(main_frame, "To Room", room_names, "to_room")
        self._create_field(main_frame, "Quantity", "quantity")
        self._create_field(main_frame, "Reason", "reason")
        self._create_field(main_frame, "Notes", "notes", multiline=True)

        ctk.CTkLabel(
            main_frame,
            text=CLINICAL_SAFETY_CHECK_NOTICE,
            wraplength=620,
            justify="left",
            font=("Arial", 10),
            text_color="orange",
        ).pack(anchor="w", pady=(8, 4))

        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=10)

        ctk.CTkButton(button_frame, text="Record Transfer", width=160, command=self._save_transfer).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", width=140, fg_color="gray", command=self.destroy).pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(main_frame, text="Enter transfer details and save.", font=("Arial", 11), text_color="gray")
        self.status_label.pack(anchor="w", pady=5)

    def _create_field(self, parent, label: str, key: str, multiline: bool = False):
        entry = self._create_voice_field(parent, label, multiline=multiline, width=360)
        self.fields[key] = entry

    def _create_combo_field(self, parent, label: str, values: list, key: str):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=8)

        ctk.CTkLabel(frame, text=label, font=("Arial", 11, "bold")).pack(anchor="w")
        combo = ctk.CTkComboBox(frame, values=values, state="readonly")
        combo.pack(fill="x", pady=5)
        self.fields[key] = combo

    def _get_item_options(self):
        items = self.inventory_service.get_all_items()
        return [f"{item.item_name} ({item.barcode})" for item in items]

    def _save_transfer(self):
        item_label = self.fields["item"].get().strip()
        from_room_name = self.fields["from_room"].get().strip()
        to_room_name = self.fields["to_room"].get().strip()
        quantity_text = self.fields["quantity"].get().strip()

        if not item_label or not from_room_name or not to_room_name or not quantity_text:
            self._set_status("Please complete all required fields", success=False)
            return

        if from_room_name == to_room_name:
            self._set_status("Source and destination rooms must differ", success=False)
            return

        try:
            quantity = int(quantity_text)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            self._set_status("Quantity must be a positive number", success=False)
            return

        item = self._find_item_by_label(item_label)
        if not item:
            self._set_status("Selected item not found", success=False)
            return

        from_room = self.room_service.get_room_by_id(self._room_id_by_name(from_room_name))
        to_room = self.room_service.get_room_by_id(self._room_id_by_name(to_room_name))
        if not from_room or not to_room:
            self._set_status("Selected rooms not found", success=False)
            return

        transfer = StockTransfer(
            item_id=item.id,
            quantity=quantity,
            from_room_id=from_room.id,
            to_room_id=to_room.id,
            transfer_date=self.time_sync_service.today(),
            transfer_time=self.time_sync_service.now().strftime("%H:%M:%S"),
            user_id=self.current_user_id,
            reason=self.fields["reason"].get().strip() or None,
            status="completed",
            notes=self.fields["notes"].get("1.0", "end").strip() or None,
        )

        confirmed = self._confirm_action(
            "Confirm Stock Transfer",
            (
                f"You are about to transfer stock.\n\n"
                f"Item: {item.item_name}\n"
                f"Quantity: {quantity}\n"
                f"From: {from_room_name}\n"
                f"To: {to_room_name}\n\n"
                f"Confirm to continue."
            ),
        )
        if not confirmed:
            self._set_status("Transfer cancelled.", success=False)
            return

        success, message, transfer_id = self.transfer_service.create_transfer(transfer)
        self._set_status(message, success=success)

        if success and self.on_save:
            self.on_save()

        if success:
            self.destroy()

    def _find_item_by_label(self, label: str) -> Optional[Item]:
        for item in self.inventory_service.get_all_items():
            if f"{item.item_name} ({item.barcode})" == label:
                return item
        return None

    def _room_id_by_name(self, room_name: str) -> Optional[int]:
        rooms = self.room_service.get_all_rooms()
        for room in rooms:
            if room.room_name == room_name:
                return room.id
        return None

    def _set_status(self, message: str, success: bool = True):
        self.status_label.configure(text=message, text_color="green" if success else "red")
        logger.info(message)

    def _confirm_action(self, title: str, message: str) -> bool:
        dialog = ActionConfirmationDialog(self, title=title, message=message)
        dialog.wait_window()
        return bool(dialog.result)
