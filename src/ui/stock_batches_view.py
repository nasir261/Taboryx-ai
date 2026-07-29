"""
Stock batches view.
UI for managing stock batches.
"""

import customtkinter as ctk
import logging

from src.models.models import StockBatch
from src.services.inventory_service import InventoryService
from src.services.room_service import ClinicalRoomService
from src.services.stock_batch_service import StockBatchService
from src.ui.stock_batch_dialog import StockBatchDialog
from src.ui.list_style_helpers import make_badge

logger = logging.getLogger(__name__)


class StockBatchesView(ctk.CTkFrame):
    """Frame for managing stock batches."""

    def __init__(self, parent):
        super().__init__(parent)
        self.batch_service = StockBatchService()
        self.inventory_service = InventoryService()
        self.room_service = ClinicalRoomService()
        self.current_batches = []
        self.item_map = {}
        self.room_map = {}

        self._setup_ui()
        self._load_batches()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="Stock Batches", font=("Arial", 19, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(top_frame, text="Add Batch", width=120, command=self._add_batch).pack(side="right", padx=5)
        ctk.CTkButton(top_frame, text="Refresh", width=100, fg_color="gray", command=self._load_batches).pack(side="right", padx=5)

        self.search_entry = ctk.CTkEntry(
            top_frame,
            width=320,
            placeholder_text="Search batch number, item, room, location, or status...",
        )
        self.search_entry.pack(side="right", padx=8)
        self.search_entry.bind("<KeyRelease>", lambda _event: self._filter_batches())

        self.status_label = ctk.CTkLabel(self, text="", font=("Arial", 14), text_color="gray")
        self.status_label.pack(anchor="w", padx=14, pady=(0, 8))

        self.batches_frame = ctk.CTkScrollableFrame(self, width=1180, height=520)
        self.batches_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._render_header()

    def _render_header(self):
        header = ctk.CTkFrame(self.batches_frame, fg_color="gray20", height=35)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)

        columns = [
            ("Batch ID", 70),
            ("Product ID", 70),
            ("Item", 170),
            ("Room ID", 70),
            ("Room", 150),
            ("Batch Number", 120),
            ("Expiry", 95),
            ("Qty", 55),
            ("Received", 95),
            ("Opened", 95),
            ("Open Days", 70),
            ("Location", 120),
            ("Status", 90),
            ("Actions", 150),
        ]
        for label, width in columns:
            ctk.CTkLabel(header, text=label, width=width, font=("Segoe UI", 12, "bold")).pack(side="left", padx=3)

    def _load_batches(self):
        self.item_map = {item.id: item for item in self.inventory_service.get_all_items() if item.id}
        self.room_map = {room.id: room for room in self.room_service.get_all_rooms() if room.id}
        self.current_batches = self.batch_service.get_all_batches()
        self._display_batches(self.current_batches)

    def _filter_batches(self):
        query = self.search_entry.get().strip().lower()
        if not query:
            self._display_batches(self.current_batches)
            return

        filtered = []
        for batch in self.current_batches:
            item_name = self.item_map.get(batch.item_id).item_name if self.item_map.get(batch.item_id) else ""
            room_name = self.room_map.get(batch.room_id).room_name if batch.room_id and self.room_map.get(batch.room_id) else ""
            haystack = " ".join(
                [
                    str(batch.batch_id or ""),
                    str(batch.product_id or ""),
                    batch.batch_number or "",
                    item_name,
                    str(batch.room_id or ""),
                    room_name,
                    batch.storage_location or "",
                    batch.status or "",
                ]
            ).lower()
            if query in haystack:
                filtered.append(batch)

        self._display_batches(filtered)

    def _display_batches(self, batches):
        for widget in self.batches_frame.winfo_children()[1:]:
            widget.destroy()

        if not batches:
            ctk.CTkLabel(self.batches_frame, text="No stock batches found.", font=("Arial", 14), text_color="gray").pack(pady=30)
            self.status_label.configure(text="No stock batches found.", text_color="gray")
            return

        self.status_label.configure(text=f"Showing {len(batches)} stock batch(es).", text_color="gray")
        for index, batch in enumerate(batches):
            self._add_batch_row(batch, index % 2 == 0)

    def _add_batch_row(self, batch: StockBatch, alternate: bool):
        bg = "#111b2e" if alternate else "#0d1727"
        row = ctk.CTkFrame(self.batches_frame, fg_color=bg, height=35)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)

        item = self.item_map.get(batch.item_id)
        room = self.room_map.get(batch.room_id) if batch.room_id else None

        values = [
            (str(batch.batch_id or ""), 70),
            (str(batch.product_id or ""), 70),
            ((item.item_name if item else "Unknown item")[:24], 170),
            (str(batch.room_id or "-"), 70),
            ((room.room_name if room else "-")[:20], 150),
            ((batch.batch_number or "-")[:18], 120),
            (batch.expiry_date.strftime("%d-%m-%Y") if batch.expiry_date else "-", 95),
            (str(batch.quantity_available), 55),
            (batch.date_received.strftime("%d-%m-%Y") if batch.date_received else "-", 95),
            (batch.opened_date.strftime("%d-%m-%Y") if batch.opened_date else "-", 95),
            (str(batch.expiry_period_after_opening) if batch.expiry_period_after_opening is not None else "-", 70),
            ((batch.storage_location or "-")[:20], 120),
        ]
        for idx, (text, width) in enumerate(values):
            if idx == 7:
                make_badge(row, text, "#0f766e", "#d1fae5", width).pack(side="left", padx=3)
            elif idx in (6, 8, 9):
                make_badge(row, text, "#1e293b", "#cbd5e1", width).pack(side="left", padx=3)
            else:
                ctk.CTkLabel(row, text=text, width=width, font=("Segoe UI", 12)).pack(side="left", padx=3)

        status_text = (batch.status or "Active")[:12]
        status_bg = "#0f766e" if status_text.lower() == "active" else "#7c2d12"
        status_fg = "#d1fae5" if status_text.lower() == "active" else "#fde68a"
        make_badge(row, f"● {status_text}", status_bg, status_fg, 90).pack(side="left", padx=3)

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="left", padx=3)
        ctk.CTkButton(actions, text="✎", width=28, height=24, fg_color="#1d4ed8", command=lambda b=batch: self._edit_batch(b)).pack(side="left", padx=2)
        ctk.CTkButton(actions, text="🗑", width=28, height=24, fg_color="#b91c1c", command=lambda b=batch: self._delete_batch(b)).pack(side="left", padx=2)

    def _add_batch(self):
        StockBatchDialog(self, on_save=self._on_batch_created)

    def _edit_batch(self, batch: StockBatch):
        StockBatchDialog(self, batch=batch, on_save=self._on_batch_updated, on_delete=self._on_batch_deleted)

    def _delete_batch(self, batch: StockBatch):
        success, message = self.batch_service.delete_batch(batch.id)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_batches()
        else:
            logger.error(message)

    def _on_batch_created(self, batch: StockBatch):
        success, message, _ = self.batch_service.create_batch(batch)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_batches()
        else:
            logger.error(message)

    def _on_batch_updated(self, batch: StockBatch):
        success, message = self.batch_service.update_batch(batch)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_batches()
        else:
            logger.error(message)

    def _on_batch_deleted(self, batch: StockBatch):
        self._delete_batch(batch)
