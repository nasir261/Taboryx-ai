"""
Stock Movements View
Display stock movement history with filters
"""

import customtkinter as ctk
from typing import Optional, Callable
import logging
from datetime import date, timedelta
from src.services.inventory_service import InventoryService
from src.ui.stock_movement_dialog import StockMovementDialog
from src.ui.list_style_helpers import make_badge

logger = logging.getLogger(__name__)


class StockMovementsView(ctk.CTkFrame):
    """Frame for displaying stock transaction history"""

    def __init__(self, parent, current_user_id: int = None, on_movement_recorded: Optional[Callable] = None):
        super().__init__(parent)
        self.inventory_service = InventoryService()
        self.current_user_id = current_user_id
        self.on_movement_recorded = on_movement_recorded
        self.current_movements = []

        self._setup_ui()
        self._load_movements()

    def _setup_ui(self):
        """Setup the UI layout"""
        # Top frame: Filters and actions
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(side="top", fill="x", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="Stock Transactions", font=("Arial", 13, "bold")).pack(
            side="left", padx=5
        )

        # Filter buttons
        ctk.CTkButton(
            top_frame, text="All", width=60, command=lambda: self._filter_movements("all")
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            top_frame,
            text="Today",
            width=60,
            command=lambda: self._filter_movements("today"),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            top_frame,
            text="This Week",
            width=80,
            command=lambda: self._filter_movements("week"),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            top_frame,
            text="This Month",
            width=100,
            command=lambda: self._filter_movements("month"),
        ).pack(side="left", padx=2)

        # Action buttons
        ctk.CTkButton(
            top_frame,
            text="Record Transaction",
            width=130,
            command=self._record_movement,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            top_frame,
            text="Refresh",
            width=80,
            fg_color="gray",
            command=self._load_movements,
        ).pack(side="left", padx=2)

        # Main frame: Movements list
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        # Create scrollable frame for movements
        self.movements_frame = ctk.CTkScrollableFrame(main_frame, width=900, height=500)
        self.movements_frame.pack(fill="both", expand=True)

        # Add header
        self._add_header()

    def _add_header(self):
        """Add table header"""
        header = ctk.CTkFrame(self.movements_frame, fg_color="gray20", height=30)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)

        columns = [
            ("Txn ID", 55),
            ("Date", 80),
            ("Time", 60),
            ("Product", 130),
            ("Batch", 70),
            ("Room", 70),
            ("Item", 150),
            ("Type", 90),
            ("Qty", 70),
            ("Before", 60),
            ("After", 60),
            ("From Room", 70),
            ("To Room", 70),
            ("Reason", 100),
            ("User", 80),
            ("Area", 80),
        ]

        for col_name, width in columns:
            label = ctk.CTkLabel(
                header, text=col_name, font=("Segoe UI", 12, "bold"), width=width
            )
            label.pack(side="left", padx=3, pady=5)

    def _load_movements(self):
        """Load all movements from database"""
        try:
            self.current_movements = self.inventory_service.get_stock_movements(limit=500)
            self._display_movements(self.current_movements)
            logger.info(f"Loaded {len(self.current_movements)} movements")
        except Exception as e:
            logger.error(f"Error loading movements: {e}")

    def _filter_movements(self, filter_type: str):
        """Filter movements by date range"""
        today = date.today()

        if filter_type == "all":
            filtered = self.current_movements
        elif filter_type == "today":
            filtered = [m for m in self.current_movements if m.movement_date == today]
        elif filter_type == "week":
            week_ago = today - timedelta(days=7)
            filtered = [m for m in self.current_movements if m.movement_date >= week_ago]
        elif filter_type == "month":
            month_ago = today - timedelta(days=30)
            filtered = [m for m in self.current_movements if m.movement_date >= month_ago]
        else:
            filtered = self.current_movements

        self._display_movements(filtered)

    def _display_movements(self, movements):
        """Display movements in the list"""
        # Clear existing movements (except header)
        for widget in self.movements_frame.winfo_children():
            if widget != self.movements_frame.winfo_children()[0]:  # Skip header
                widget.destroy()

        # Add movements
        for idx, movement in enumerate(movements):
            self._add_movement_row(movement, idx % 2 == 0)

        if not movements:
            no_data = ctk.CTkLabel(
                self.movements_frame,
                text="No stock transactions recorded",
                font=("Arial", 12),
                text_color="gray",
            )
            no_data.pack(pady=20)

    def _add_movement_row(self, movement, alternate_bg: bool):
        """Add a single movement row"""
        bg_color = "#111b2e" if alternate_bg else "#0d1727"

        row = ctk.CTkFrame(self.movements_frame, fg_color=bg_color, height=35)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)

        # Get item name
        try:
            item = self.inventory_service.get_item_by_id(movement.item_id)
            item_name = item.item_name if item else f"Item {movement.item_id}"
        except:
            item_name = f"Item {movement.item_id}"

        # Format data
        if movement.movement_date:
            date_str = (
                movement.movement_date.strftime("%d-%m-%Y")
                if hasattr(movement.movement_date, "strftime")
                else str(movement.movement_date)
            )
        else:
            date_str = "-"

        if movement.movement_time:
            time_str = (
                movement.movement_time.strftime("%H:%M:%S")
                if hasattr(movement.movement_time, "strftime")
                else str(movement.movement_time)
            )
        else:
            time_str = "-"

        qty_str = str(movement.quantity)
        qty_before = str(movement.quantity_before) if movement.quantity_before is not None else "-"
        qty_after = str(movement.quantity_after) if movement.quantity_after is not None else "-"
        reason = movement.reason or "-"
        user_id = str(movement.user_id) if movement.user_id else "-"
        area = movement.patient_area or "-"
        batch_id = str(movement.batch_id) if movement.batch_id else "-"
        room_id = str(movement.room_id) if movement.room_id else "-"
        from_room_id = str(movement.from_room_id) if movement.from_room_id else "-"
        to_room_id = str(movement.to_room_id) if movement.to_room_id else "-"

        # Add columns
        columns = [
            (str(movement.transaction_id or "-"), 55),
            (date_str, 80),
            (time_str, 60),
            (str(movement.product_id), 130),
            (batch_id, 70),
            (room_id, 70),
            (f"💊 {item_name[:18]}", 150),
            (movement.movement_type[:10], 90),
            (qty_str, 70),
            (qty_before, 60),
            (qty_after, 60),
            (from_room_id, 70),
            (to_room_id, 70),
            (reason[:15], 100),
            (user_id, 80),
            (area[:15], 80),
        ]

        for idx, (col_text, width) in enumerate(columns):
            if idx in (7, 8, 9, 10):
                bg = "#0f766e" if idx == 8 else "#1e293b"
                fg = "#d1fae5" if idx == 8 else "#cbd5e1"
                if idx == 7:
                    type_lower = movement.movement_type.lower()
                    bg = "#1d4ed8" if type_lower in {"received", "returned"} else "#7c2d12" if type_lower in {"expired", "disposed", "lost", "damaged"} else "#6d28d9"
                    fg = "#dbeafe" if type_lower in {"received", "returned"} else "#fde68a"
                make_badge(row, col_text, bg, fg, width).pack(side="left", padx=3, pady=5)
            else:
                label = ctk.CTkLabel(row, text=col_text, font=("Segoe UI", 12), width=width)
                label.pack(side="left", padx=3, pady=5)

    def _record_movement(self):
        """Open stock movement recording dialog"""
        try:
            dialog = StockMovementDialog(
                self,
                current_user_id=self.current_user_id,
                on_save=self._on_movement_saved,
            )
        except Exception as e:
            logger.error(f"Error opening movement dialog: {e}")

    def _on_movement_saved(self):
        """Handle movement saved"""
        self._load_movements()
        if self.on_movement_recorded:
            self.on_movement_recorded()
