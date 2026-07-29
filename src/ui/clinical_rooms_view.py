"""
Clinical Rooms View
Manage clinical rooms and view room-specific inventory
"""

import customtkinter as ctk
import logging
from datetime import date
from typing import Optional
from src.services.room_service import ClinicalRoomService
from src.models.models import ClinicalRoom
from src.ui.clinical_room_dialog import ClinicalRoomDialog
from src.ui.list_style_helpers import make_badge

logger = logging.getLogger(__name__)


class ClinicalRoomsView(ctk.CTkFrame):
    """Frame for managing clinical rooms"""

    def __init__(self, parent):
        super().__init__(parent)
        self.room_service = ClinicalRoomService()
        self.current_rooms = []
        self.selected_room: Optional[ClinicalRoom] = None

        self._setup_ui()
        self._load_rooms()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        title = ctk.CTkLabel(top_frame, text="Clinical Rooms", font=("Segoe UI", 19, "bold"))
        title.pack(side="left", padx=5)

        ctk.CTkButton(top_frame, text="Add Room", width=120, command=self._add_room).pack(side="right", padx=5)
        ctk.CTkButton(top_frame, text="Refresh", width=100, fg_color="gray", command=self._load_rooms).pack(side="right", padx=5)

        self.rooms_frame = ctk.CTkScrollableFrame(self, width=1100, height=420)
        self.rooms_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._add_header()

        self.room_details_frame = ctk.CTkFrame(self)
        self.room_details_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _add_header(self):
        header = ctk.CTkFrame(self.rooms_frame, fg_color="gray20", height=34)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)

        columns = [
            ("Room Name", 200),
            ("Type", 120),
            ("Floor", 70),
            ("Location", 250),
            ("Items", 60),
            ("Actions", 260),
        ]

        for text, width in columns:
            ctk.CTkLabel(header, text=text, font=("Segoe UI", 12, "bold"), width=width).pack(side="left", padx=5)

    def _load_rooms(self):
        self.current_rooms = self.room_service.get_all_rooms()
        self._display_rooms(self.current_rooms)
        self._clear_room_details()

    def _display_rooms(self, rooms):
        for widget in self.rooms_frame.winfo_children()[1:]:
            widget.destroy()

        for idx, room in enumerate(rooms):
            self._add_room_row(room, alternate=(idx % 2 == 0))

    def _add_room_row(self, room: ClinicalRoom, alternate: bool):
        bg = "#111b2e" if alternate else "#0d1727"
        row = ctk.CTkFrame(self.rooms_frame, fg_color=bg, height=34)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)

        ctk.CTkLabel(row, text=f"🏥 {room.room_name}", width=200, font=("Segoe UI", 12)).pack(side="left", padx=5)
        make_badge(row, room.room_type or "-", "#1e293b", "#cbd5e1", 120).pack(side="left", padx=5)
        make_badge(row, str(room.floor or "-"), "#334155", "#e2e8f0", 70).pack(side="left", padx=5)
        ctk.CTkLabel(row, text=room.location_description or "-", width=250, font=("Segoe UI", 12)).pack(side="left", padx=5)

        item_count = self.room_service.get_room_item_count(room.room_name)
        make_badge(row, str(item_count), "#0f766e", "#d1fae5", 60).pack(side="left", padx=5)

        actions_frame = ctk.CTkFrame(row, fg_color="transparent")
        actions_frame.pack(side="left", padx=5)

        ctk.CTkButton(actions_frame, text="👁", width=28, height=24, fg_color="#1f6aa5", command=lambda r=room: self._view_room_items(r)).pack(side="left", padx=2)
        ctk.CTkButton(actions_frame, text="✎", width=28, height=24, fg_color="#1d4ed8", command=lambda r=room: self._edit_room(r)).pack(side="left", padx=2)
        ctk.CTkButton(actions_frame, text="🗑", width=28, height=24, fg_color="#b91c1c", command=lambda r=room: self._delete_room(r)).pack(side="left", padx=2)

    def _view_room_items(self, room: ClinicalRoom):
        self.selected_room = room
        self._render_room_details(room)

    def _render_room_details(self, room: ClinicalRoom):
        for widget in self.room_details_frame.winfo_children():
            widget.destroy()

        title = ctk.CTkLabel(self.room_details_frame, text=f"Inventory for {room.room_name}", font=("Segoe UI", 17, "bold"))
        title.pack(anchor="w", pady=(0, 10))

        items = self.room_service.get_items_in_room(room.room_name)
        if not items:
            ctk.CTkLabel(self.room_details_frame, text="No items assigned to this room.", font=("Segoe UI", 14), text_color="gray").pack(anchor="w", pady=10)
            return

        table_frame = ctk.CTkFrame(self.room_details_frame)
        table_frame.pack(fill="both", expand=True)

        headers = ["Item", "Barcode", "Category", "Qty", "Expiry"]
        widths = [280, 140, 120, 60, 120]
        header_row = ctk.CTkFrame(table_frame, fg_color="gray20", height=32)
        header_row.pack(fill="x", padx=5, pady=2)
        header_row.pack_propagate(False)
        for text, width in zip(headers, widths):
            ctk.CTkLabel(header_row, text=text, width=width, font=("Segoe UI", 12, "bold")).pack(side="left", padx=5)

        for item in items:
            row = ctk.CTkFrame(table_frame, fg_color="#111b2e", height=30)
            row.pack(fill="x", padx=5, pady=1)
            row.pack_propagate(False)
            expiry = item.expiry_date.strftime("%d-%m-%Y") if item.expiry_date else "-"
            columns = [(f"💊 {item.item_name}", 280), (item.barcode or "-", 140), (item.category or "-", 120)]
            for text, width in columns:
                ctk.CTkLabel(row, text=text, width=width, font=("Segoe UI", 12)).pack(side="left", padx=5)
            make_badge(row, str(item.current_quantity), "#0f766e", "#d1fae5", 60).pack(side="left", padx=5)
            expiry_bg = "#7c2d12" if item.expiry_date and item.expiry_date < date.today() else "#1e293b"
            expiry_fg = "#fde68a" if expiry_bg == "#7c2d12" else "#cbd5e1"
            make_badge(row, expiry, expiry_bg, expiry_fg, 120).pack(side="left", padx=5)

    def _clear_room_details(self):
        for widget in self.room_details_frame.winfo_children():
            widget.destroy()

    def _add_room(self):
        ClinicalRoomDialog(self, on_save=self._on_room_created)

    def _edit_room(self, room: ClinicalRoom):
        ClinicalRoomDialog(self, room=room, on_save=self._on_room_updated, on_delete=self._on_room_deleted)

    def _delete_room(self, room: ClinicalRoom):
        try:
            self.room_service.delete_room(room.id)
            self._load_rooms()
            if self.selected_room and self.selected_room.id == room.id:
                self._clear_room_details()
        except Exception as e:
            logger.error(f"Error deleting room: {e}")

    def _on_room_deleted(self, room: ClinicalRoom):
        self._delete_room(room)

    def _on_room_created(self, room: ClinicalRoom):
        try:
            self.room_service.create_room(room)
            self._load_rooms()
        except Exception as e:
            logger.error(f"Error creating room: {e}")

    def _on_room_updated(self, room: ClinicalRoom):
        try:
            self.room_service.update_room(room)
            self._load_rooms()
        except Exception as e:
            logger.error(f"Error updating room: {e}")
