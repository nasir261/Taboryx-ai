"""
Stock Transfers View
UI for managing stock transfers between rooms.
"""

import customtkinter as ctk
import logging
from src.services.transfer_service import TransferService
from src.services.room_service import ClinicalRoomService
from src.services.inventory_service import InventoryService
from src.ui.stock_transfer_dialog import StockTransferDialog
from src.models.models import StockTransfer

logger = logging.getLogger(__name__)


class StockTransfersView(ctk.CTkFrame):
    """Frame for viewing and creating stock transfers"""

    def __init__(self, parent, current_user_id: int):
        super().__init__(parent)
        self.transfer_service = TransferService()
        self.room_service = ClinicalRoomService()
        self.inventory_service = InventoryService()
        self.current_user_id = current_user_id
        self.transfers = []

        self._setup_ui()
        self._load_transfers()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        title = ctk.CTkLabel(top_frame, text="Stock Transfers", font=("Arial", 16, "bold"))
        title.pack(side="left", padx=5)

        ctk.CTkButton(top_frame, text="New Transfer", width=130, command=self._new_transfer).pack(side="right", padx=5)
        ctk.CTkButton(top_frame, text="Refresh", width=100, fg_color="gray", command=self._load_transfers).pack(side="right", padx=5)

        self.transfers_frame = ctk.CTkScrollableFrame(self, width=1100, height=520)
        self.transfers_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._render_header()

    def _render_header(self):
        header = ctk.CTkFrame(self.transfers_frame, fg_color="gray20", height=35)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)

        labels = [
            "Transfer ID",
            "Item",
            "Qty",
            "From Room",
            "To Room",
            "Date",
            "Time",
            "User",
            "Reason",
            "Status",
        ]
        widths = [80, 200, 60, 140, 140, 90, 90, 80, 120, 90]

        for text, width in zip(labels, widths):
            ctk.CTkLabel(header, text=text, font=("Arial", 10, "bold"), width=width).pack(side="left", padx=3)

    def _load_transfers(self):
        for widget in self.transfers_frame.winfo_children()[1:]:
            widget.destroy()

        self.transfers = self.transfer_service.get_transfers(limit=200)
        if not self.transfers:
            ctk.CTkLabel(self.transfers_frame, text="No stock transfers recorded.", font=("Arial", 11), text_color="gray").pack(pady=30)
            return

        for transfer in self.transfers:
            self._add_transfer_row(transfer)

    def _add_transfer_row(self, transfer: StockTransfer):
        row = ctk.CTkFrame(self.transfers_frame, fg_color="gray15", height=35)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)

        item = self.inventory_service.get_item_by_id(transfer.item_id)
        item_label = item.item_name if item else f"Item {transfer.item_id}"
        from_room = self.room_service.get_room_by_id(transfer.from_room_id)
        to_room = self.room_service.get_room_by_id(transfer.to_room_id)

        columns = [
            str(transfer.id),
            item_label,
            str(transfer.quantity),
            from_room.room_name if from_room else "-",
            to_room.room_name if to_room else "-",
            str(transfer.transfer_date or ""),
            str(transfer.transfer_time or ""),
            str(transfer.user_id),
            transfer.reason or "",
            transfer.status,
        ]
        widths = [80, 200, 60, 140, 140, 90, 90, 80, 120, 90]

        for text, width in zip(columns, widths):
            ctk.CTkLabel(row, text=text, width=width).pack(side="left", padx=3)

    def _new_transfer(self):
        StockTransferDialog(self, self.current_user_id, on_save=self._load_transfers)
