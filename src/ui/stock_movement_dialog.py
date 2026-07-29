"""
Stock Movement Dialog
Dialog for recording inventory stock movements
"""

import customtkinter as ctk
from typing import Optional, Callable
from datetime import datetime, date
import logging
from src.models.models import StockMovement, Item
from src.services.inventory_service import InventoryService
from src.services.auth_service import AuthenticationService
from src.services.room_service import ClinicalRoomService
from src.services.stock_batch_service import StockBatchService
from src.services.time_sync_service import get_time_sync_service
from src.ui.voice_typing_mixin import VoiceTypingMixin
from src.config import (
    StockMovementType,
    MAJOR_STOCK_ADJUSTMENT_CONFIRM_THRESHOLD,
    CLINICAL_SAFETY_CHECK_NOTICE,
)
from src.ui.action_confirmation_dialog import ActionConfirmationDialog

logger = logging.getLogger(__name__)


class StockMovementDialog(VoiceTypingMixin, ctk.CTkToplevel):
    """Dialog for recording stock movements"""

    def __init__(
        self,
        parent,
        item: Optional[Item] = None,
        current_user_id: int = None,
        on_save: Optional[Callable] = None,
    ):
        super().__init__(parent)
        self.title("Record Stock Movement")
        self.geometry("600x700")
        self.resizable(False, False)
        self.grab_set()

        self.item = item
        self.current_user_id = current_user_id
        self.on_save = on_save
        self.inventory_service = InventoryService()
        self.room_service = ClinicalRoomService()
        self.stock_batch_service = StockBatchService()
        self.time_sync_service = get_time_sync_service()
        self.fields = {}
        self._initialize_voice_typing()

        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog UI"""
        # Main scrollable frame
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title = "Record Stock Movement"
        if self.item:
            title += f" - {self.item.item_name}"
        ctk.CTkLabel(main_frame, text=title, font=("Arial", 14, "bold")).pack(
            anchor="w", pady=(0, 20)
        )

        # Item selection (if not provided)
        if not self.item:
            self._create_item_selector(main_frame)

        # Movement type selection
        self._create_movement_type_selector(main_frame)

        # Quantity field
        self.fields["quantity"] = self._create_voice_field(main_frame, "Quantity *")

        # Reason field
        self.fields["reason"] = self._create_voice_field(main_frame, "Reason")

        self._create_room_selector(main_frame)
        self._create_batch_selector(main_frame)

        # Patient area field
        self.fields["patient_area"] = self._create_voice_field(main_frame, "Patient Area / Location")

        # From location field (for transfers)
        self.fields["from_location"] = self._create_voice_field(main_frame, "From Location (for transfers)")

        # To location field (for transfers)
        self.fields["to_location"] = self._create_voice_field(main_frame, "To Location (for transfers)")

        # Batch number field
        self.fields["batch_number"] = self._create_voice_field(main_frame, "Batch Number")

        # Notes field
        self.fields["notes"] = self._create_voice_field(main_frame, "Additional Notes", multiline=True)

        ctk.CTkLabel(
            main_frame,
            text=CLINICAL_SAFETY_CHECK_NOTICE,
            wraplength=540,
            justify="left",
            font=("Arial", 10),
            text_color="orange",
        ).pack(anchor="w", pady=(8, 4))

        # Button frame
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=20)

        ctk.CTkButton(
            button_frame, text="Record Movement", command=self._save_movement, width=150
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame, text="Cancel", fg_color="gray", command=self.destroy, width=150
        ).pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(main_frame, text="", font=("Arial", 11), text_color="gray")
        self.status_label.pack(anchor="w", pady=(5, 0))

    def _create_item_selector(self, parent):
        """Create item selection field"""
        item_frame = ctk.CTkFrame(parent)
        item_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(item_frame, text="Item *", font=("Arial", 11, "bold")).pack(anchor="w")

        # Get all items for dropdown
        try:
            all_items = self.inventory_service.get_all_items()
            item_names = [f"{item.item_name} ({item.barcode})" for item in all_items]
            self.fields["item"] = ctk.CTkComboBox(
                item_frame, values=item_names, state="readonly"
            )
            self.fields["item"].pack(fill="x", pady=5)
        except Exception as e:
            logger.error(f"Error loading items: {e}")

    def _create_movement_type_selector(self, parent):
        """Create movement type selection"""
        type_frame = ctk.CTkFrame(parent)
        type_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(type_frame, text="Movement Type *", font=("Arial", 11, "bold")).pack(
            anchor="w"
        )

        movement_types = [
            ("Received", "RECEIVED"),
            ("Used", "USED"),
            ("Issued", "ISSUED"),
            ("Transferred", "TRANSFERRED"),
            ("Quarantined", "QUARANTINED"),
            ("Returned", "RETURNED"),
            ("Expired", "EXPIRED"),
            ("Disposed", "DISPOSED"),
            ("Adjusted", "ADJUSTED"),
            ("Lost", "LOST"),
            ("Damaged", "DAMAGED"),
        ]

        type_names = [name for name, _ in movement_types]
        self.fields["movement_type"] = ctk.CTkComboBox(
            type_frame, values=type_names, state="readonly"
        )
        self.fields["movement_type"].pack(fill="x", pady=5)
        self.movement_type_map = {name: value for name, value in movement_types}

    def _create_room_selector(self, parent):
        room_frame = ctk.CTkFrame(parent)
        room_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(room_frame, text="Room", font=("Arial", 11, "bold")).pack(anchor="w")
        rooms = self.room_service.get_all_rooms()
        room_values = [""] + [f"{room.id} - {room.room_name}" for room in rooms if room.id]
        self.fields["room_id"] = ctk.CTkComboBox(room_frame, values=room_values, state="readonly")
        self.fields["room_id"].pack(fill="x", pady=5)
        self.fields["room_id"].set("")

    def _create_batch_selector(self, parent):
        batch_frame = ctk.CTkFrame(parent)
        batch_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(batch_frame, text="Batch", font=("Arial", 11, "bold")).pack(anchor="w")
        batches = self.stock_batch_service.get_all_batches()
        batch_values = [""] + [f"{batch.id} - {batch.batch_number}" for batch in batches if batch.id]
        self.fields["batch_id"] = ctk.CTkComboBox(batch_frame, values=batch_values, state="readonly")
        self.fields["batch_id"].pack(fill="x", pady=5)
        self.fields["batch_id"].set("")

    def _save_movement(self):
        """Validate and save stock movement"""
        try:
            # Get item
            if self.item:
                item = self.item
            else:
                item_name = self.fields["item"].get()
                if not item_name:
                    self._show_error("Please select an item")
                    return
                # Extract item from list
                all_items = self.inventory_service.get_all_items()
                item = None
                for i in all_items:
                    if f"{i.item_name} ({i.barcode})" == item_name:
                        item = i
                        break
                if not item:
                    self._show_error("Item not found")
                    return

            # Validate quantity
            try:
                quantity = int(self.fields["quantity"].get())
                if quantity <= 0:
                    self._show_error("Quantity must be greater than 0")
                    return
            except ValueError:
                self._show_error("Quantity must be a valid number")
                return

            # Get movement type
            movement_type_name = self.fields["movement_type"].get()
            if not movement_type_name:
                self._show_error("Please select a movement type")
                return
            movement_type = self.movement_type_map.get(movement_type_name)

            # Determine quantity change based on movement type
            if movement_type in ["ISSUED", "EXPIRED", "DISPOSED", "LOST", "DAMAGED"]:
                quantity_change = -quantity
            elif movement_type == "USED":
                quantity_change = -quantity
            elif movement_type == "QUARANTINED":
                quantity_change = -quantity
            else:
                quantity_change = quantity

            room_id = self._parse_prefixed_id(self.fields["room_id"].get().strip())
            batch_id = self._parse_prefixed_id(self.fields["batch_id"].get().strip())

            if self.inventory_service.requires_movement_confirmation(movement_type, quantity_change):
                if movement_type == "ADJUSTED":
                    message = (
                        f"This is a major stock adjustment (threshold: {MAJOR_STOCK_ADJUSTMENT_CONFIRM_THRESHOLD}).\n\n"
                        f"Item: {item.item_name}\nAdjustment: {quantity_change:+d}\n\nConfirm to continue."
                    )
                else:
                    message = (
                        f"You are about to record a {movement_type_name.lower()} movement.\n\n"
                        f"Item: {item.item_name}\nQuantity: {quantity}\n\nConfirm to continue."
                    )
                confirmed = self._confirm_action("Confirm High-Risk Movement", message)
                if not confirmed:
                    logger.info("Stock movement confirmation cancelled by user.")
                    return

            # Create stock movement
            movement = StockMovement(
                item_id=item.id,
                movement_type=movement_type,
                transaction_quantity=quantity,
                quantity_change=quantity_change,
                batch_id=batch_id,
                room_id=room_id,
                user_id=self.current_user_id,
                movement_date=self.time_sync_service.today(),
                movement_time=self.time_sync_service.now().time(),
                reason=self.fields["reason"].get().strip() or None,
                patient_area=self.fields["patient_area"].get().strip() or None,
                from_location=self.fields["from_location"].get().strip() or None,
                to_location=self.fields["to_location"].get().strip() or None,
                batch_number=self.fields["batch_number"].get().strip() or None,
                notes=self.fields["notes"].get("1.0", "end").strip() or None,
            )

            # Log movement
            success, msg, movement_id = self.inventory_service.log_stock_movement(movement)

            if success:
                logger.info(
                    f"Stock movement recorded: {item.item_name} - {movement_type} - Qty: {quantity_change}"
                )
                if self.on_save:
                    self.on_save()
                self.destroy()
            else:
                self._show_error(msg)

        except Exception as e:
            logger.error(f"Error saving movement: {e}")
            self._show_error(f"Error: {str(e)}")

    def _confirm_action(self, title: str, message: str) -> bool:
        dialog = ActionConfirmationDialog(self, title=title, message=message)
        dialog.wait_window()
        return bool(dialog.result)

    def _show_error(self, message: str):
        """Show error message"""
        logger.error(message)
        print(f"ERROR: {message}")

    @staticmethod
    def _parse_prefixed_id(value: str) -> Optional[int]:
        if not value:
            return None
        prefix = value.split(" - ", 1)[0].strip()
        return int(prefix) if prefix.isdigit() else None
