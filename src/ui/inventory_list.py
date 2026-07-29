"""
Inventory List View
Displays all items with search, filter, and action buttons
"""

import customtkinter as ctk
from typing import Optional, Callable
import logging
from src.services.inventory_service import InventoryService
from src.services.supplier_service import SupplierService
from src.ui.item_detail import ItemDetailWindow
from src.models.models import Item

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


class InventoryListView(ctk.CTkFrame):
    """Frame for displaying inventory items with search and actions"""

    def __init__(self, parent, on_item_selected: Optional[Callable] = None):
        super().__init__(parent)
        self.inventory_service = InventoryService()
        self.supplier_service = SupplierService()
        self.on_item_selected = on_item_selected
        self.current_items = []
        self.selected_item_id = None
        self._refresh_supplier_map()

        self._setup_ui()
        self._load_items()

    def _refresh_supplier_map(self):
        """Refresh supplier lookup map"""
        suppliers = self.supplier_service.get_all_suppliers()
        self.supplier_map = {supplier.id: supplier.supplier_name for supplier in suppliers if supplier.id}

    def _setup_ui(self):
        """Setup the UI layout"""
        # Top frame: Search and filters
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(side="top", fill="x", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="Search:", font=("Arial", 12, "bold")).pack(
            side="left", padx=5
        )

        self.search_entry = ctk.CTkEntry(
            top_frame, placeholder_text="Item name, product code, barcode, manufacturer, or category...", width=340
        )
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self._search_items())

        ctk.CTkButton(
            top_frame, text="Add Item", width=100, command=self._on_add_item
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            top_frame,
            text="Refresh",
            width=80,
            fg_color="gray",
            command=self._load_items,
        ).pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color="gray")
        self.status_label.pack(anchor="w", padx=14, pady=(0, 8))

        # Main frame: Table/List
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        # Create treeview-like table using CTkFrame and labels
        self.items_frame = ctk.CTkScrollableFrame(main_frame, width=900, height=400)
        self.items_frame.pack(fill="both", expand=True)

        # Add header
        self._add_header()

    def _add_header(self):
        """Add table header"""
        header = ctk.CTkFrame(self.items_frame, fg_color="gray20", height=30)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)
 
        columns = [
            ("# ", 34),
            ("Medicine", 128),
            ("Code", 86),
            ("Barcode", 92),
            ("Cat", 70),
            ("Maker", 98),
            ("Supplier", 106),
            ("Qty", 52),
            ("Min", 46),
            ("Target", 52),
            ("State", 76),
            ("Expiry", 72),
            ("Action", 96),
        ]

        for col_name, width in columns:
            label = ctk.CTkLabel(
                header, text=col_name, font=("Segoe UI", 12, "bold"), width=width
            )
            label.pack(side="left", padx=5, pady=5)

    def _load_items(self):
        """Load all items from database"""
        try:
            self._refresh_supplier_map()
            self.current_items = self.inventory_service.get_all_items()
            self._display_items(self.current_items)
            logger.info(f"Loaded {len(self.current_items)} items")
        except Exception as e:
            logger.error(f"Error loading items: {e}")
            self._show_error("Failed to load items")

    def _search_items(self):
        """Search items based on search entry"""
        search_text = self.search_entry.get().lower()
        if not search_text:
            self._display_items(self.current_items)
            return

        filtered = [
            item
            for item in self.current_items
            if search_text in item.name.lower()
            or (item.product_code and search_text in item.product_code.lower())
            or (item.barcode and search_text in item.barcode.lower())
            or (item.category and search_text in item.category.lower())
            or (item.manufacturer and search_text in item.manufacturer.lower())
        ]
        self._display_items(filtered)

    def _display_items(self, items):
        """Display items in the list"""
        # Clear existing items
        for widget in self.items_frame.winfo_children():
            if widget != self.items_frame.winfo_children()[0]:  # Skip header
                widget.destroy()

        # Add items
        for idx, item in enumerate(items):
            self._add_item_row(item, idx % 2 == 0)

    def _add_item_row(self, item: Item, alternate_bg: bool):
        """Add a single item row to the display"""
        if item.stock_status == "LOW_STOCK":
            bg_color = "#132036" if alternate_bg else "#0f1d33"
        elif item.stock_status == "OUT_OF_STOCK":
            bg_color = "#271626" if alternate_bg else "#21111d"
        elif item.stock_status == "OVERSTOCK":
            bg_color = "#172235" if alternate_bg else "#122033"
        else:
            bg_color = "#111b2e" if alternate_bg else "#0d1727"

        row = ctk.CTkFrame(self.items_frame, fg_color=bg_color, height=32)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)

        # Bind click event
        row.bind(
            "<Button-1>",
            lambda e, item_id=item.id: self._on_item_click(item_id),
        )

        # ID
        ctk.CTkLabel(row, text=str(item.id), width=34, font=("Segoe UI", 12)).pack(side="left", padx=5)

        # Name
        ctk.CTkLabel(row, text=f"💊 {item.name[:18]}", width=128, font=("Segoe UI", 12)).pack(side="left", padx=5)

        product_code = item.product_code or "-"
        ctk.CTkLabel(row, text=product_code[:14], width=86, font=("Segoe UI", 12)).pack(side="left", padx=5)

        # Barcode
        barcode = item.barcode or "-"
        ctk.CTkLabel(row, text=barcode[:14], width=92, font=("Segoe UI", 12)).pack(side="left", padx=5)

        # Category
        category = item.category or "-"
        ctk.CTkLabel(row, text=category[:12], width=70, font=("Segoe UI", 12)).pack(side="left", padx=5)

        manufacturer = item.manufacturer or "-"
        ctk.CTkLabel(row, text=manufacturer[:14], width=98, font=("Segoe UI", 12)).pack(side="left", padx=5)
 
        # Supplier
        supplier_name = self.supplier_map.get(item.supplier_id, "-") if item.supplier_id else "-"
        ctk.CTkLabel(row, text=supplier_name[:14], width=106, font=("Segoe UI", 12)).pack(side="left", padx=5)
 
        # Quantity
        self._make_badge(row, str(item.current_quantity), "#0f766e", "#d1fae5", 52).pack(side="left", padx=5)

        # Min
        self._make_badge(row, str(item.minimum_quantity), "#334155", "#e2e8f0", 46).pack(side="left", padx=5)

        # Max
        self._make_badge(row, str(item.maximum_quantity), "#334155", "#e2e8f0", 52).pack(side="left", padx=5)

        status_text = f"{'●' if item.is_active else '○'} {'Active' if item.is_active else 'Inactive'}"
        status_bg = "#0f766e" if item.is_active else "#7f1d1d"
        status_fg = "#d1fae5" if item.is_active else "#fecaca"
        self._make_badge(row, status_text, status_bg, status_fg, 76).pack(side="left", padx=5)

        # Expiry
        expiry = item.expiry_date.strftime("%d-%m-%Y") if item.expiry_date else "-"
        expiry_bg = "#7c2d12" if item.is_expired else "#1e293b"
        expiry_fg = "#fde68a" if item.is_expired else "#cbd5e1"
        self._make_badge(row, expiry, expiry_bg, expiry_fg, 72).pack(side="left", padx=5)

        # Actions
        actions_frame = ctk.CTkFrame(row, fg_color="transparent")
        actions_frame.pack(side="left", padx=5)

        ctk.CTkButton(
            actions_frame,
            text="✎",
            width=28,
            height=24,
            font=("Segoe UI", 12),
            fg_color="#1d4ed8",
            command=lambda: self._on_edit_item(item.id),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            actions_frame,
            text="🗑",
            width=28,
            height=24,
            font=("Segoe UI", 12),
            fg_color="#b91c1c",
            command=lambda: self._on_delete_item(item.id),
        ).pack(side="left", padx=2)

    def _make_badge(self, parent, text: str, bg_color: str, text_color: str, width: int):
        badge = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=8, width=width, height=22)
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text=text, text_color=text_color, font=("Segoe UI", 12, "bold")).pack(expand=True)
        return badge

    def _on_item_click(self, item_id: int):
        """Handle item row click"""
        self.selected_item_id = item_id
        if self.on_item_selected:
            self.on_item_selected(item_id)

    def _on_add_item(self):
        """Handle add item button"""
        logger.info("Add item clicked")
        initial_name = self.search_entry.get().strip()
        ItemDetailWindow(self, on_save=self.refresh, initial_name=initial_name if initial_name else None)
 
    def _on_edit_item(self, item_id: int):
        """Handle edit item button"""
        logger.info(f"Edit item {item_id}")
        item = self.inventory_service.get_item_by_id(item_id)
        if item:
            ItemDetailWindow(self, item=item, on_save=self.refresh)
        else:
            logger.error(f"Item not found for edit: {item_id}")
 
    def _on_delete_item(self, item_id: int):
        """Handle delete item button"""
        logger.info(f"Delete item {item_id}")
        dialog = AdminPasswordDialog(self)
        dialog.wait_window()
        if dialog.result is None:
            self.status_label.configure(text="Delete item cancelled.", text_color="gray")
            return

        success, message = self.inventory_service.delete_item_with_admin_password(item_id, dialog.result)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self.refresh()
        else:
            logger.error(f"Failed to delete item {item_id}: {message}")

    def _show_error(self, message: str):
        """Show error message"""
        logger.error(message)
        # TODO: Show error dialog

    def refresh(self):
        """Refresh the item list"""
        self._load_items()
