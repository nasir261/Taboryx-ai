"""
Suppliers View
UI for managing suppliers.
"""

import customtkinter as ctk
import logging
from src.services.supplier_service import SupplierService
from src.ui.supplier_dialog import SupplierDialog
from src.models.models import Supplier
from src.ui.list_style_helpers import make_badge

logger = logging.getLogger(__name__)


class SuppliersView(ctk.CTkFrame):
    """Frame for supplier management"""

    def __init__(self, parent):
        super().__init__(parent)
        self.supplier_service = SupplierService()
        self.current_suppliers = []

        self._setup_ui()
        self._load_suppliers()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        title = ctk.CTkLabel(top_frame, text="Supplier Management", font=("Segoe UI", 19, "bold"))
        title.pack(side="left", padx=5)

        ctk.CTkButton(top_frame, text="Add Supplier", width=140, command=self._add_supplier).pack(side="right", padx=5)
        ctk.CTkButton(top_frame, text="Refresh", width=100, fg_color="gray", command=self._load_suppliers).pack(side="right", padx=5)

        self.suppliers_frame = ctk.CTkScrollableFrame(self, width=1100, height=520)
        self.suppliers_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._render_header()

    def _render_header(self):
        header = ctk.CTkFrame(self.suppliers_frame, fg_color="gray20", height=35)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)

        columns = ["Name", "Contact", "Email", "Phone", "Lead Time", "Status", "Actions"]
        widths = [220, 180, 180, 120, 90, 90, 170]

        for text, width in zip(columns, widths):
            ctk.CTkLabel(header, text=text, font=("Segoe UI", 12, "bold"), width=width).pack(side="left", padx=3)

    def _load_suppliers(self):
        for widget in self.suppliers_frame.winfo_children()[1:]:
            widget.destroy()

        self.current_suppliers = self.supplier_service.get_all_suppliers()
        if not self.current_suppliers:
            ctk.CTkLabel(self.suppliers_frame, text="No suppliers configured.", font=("Arial", 12), text_color="gray").pack(pady=30)
            return

        for supplier in self.current_suppliers:
            self._add_supplier_row(supplier)

    def _add_supplier_row(self, supplier: Supplier):
        row = ctk.CTkFrame(self.suppliers_frame, fg_color="#111b2e", height=35)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)

        columns = [
            (f"🏭 {supplier.supplier_name}", 220),
            (supplier.contact_person or "-", 180),
            (supplier.email or "-", 180),
            (supplier.telephone or "-", 120),
            (str(supplier.lead_time_days or "-"), 90),
        ]

        for text, width in columns:
            ctk.CTkLabel(row, text=text, width=width, font=("Segoe UI", 12)).pack(side="left", padx=3)

        make_badge(
            row,
            f"● {'Active' if supplier.is_active else 'Inactive'}",
            "#0f766e" if supplier.is_active else "#7c2d12",
            "#d1fae5" if supplier.is_active else "#fde68a",
            90,
        ).pack(side="left", padx=3)

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="left", padx=3)

        ctk.CTkButton(actions, text="✎", width=28, height=24, fg_color="#1d4ed8", command=lambda s=supplier: self._edit_supplier(s)).pack(side="left", padx=2)
        ctk.CTkButton(actions, text="🗑", width=28, height=24, fg_color="#b91c1c", command=lambda s=supplier: self._delete_supplier(s)).pack(side="left", padx=2)

    def _add_supplier(self):
        SupplierDialog(self, on_save=self._on_supplier_saved)

    def _edit_supplier(self, supplier: Supplier):
        SupplierDialog(self, supplier=supplier, on_save=self._on_supplier_updated)

    def _delete_supplier(self, supplier: Supplier):
        success, message = self.supplier_service.delete_supplier(supplier.id)
        if success:
            self._load_suppliers()
        else:
            logger.error(message)

    def _on_supplier_saved(self, supplier: Supplier):
        success, message, supplier_id = self.supplier_service.create_supplier(supplier)
        if success:
            self._load_suppliers()
        else:
            logger.error(message)

    def _on_supplier_updated(self, supplier: Supplier):
        success, message = self.supplier_service.update_supplier(supplier)
        if success:
            self._load_suppliers()
        else:
            logger.error(message)
