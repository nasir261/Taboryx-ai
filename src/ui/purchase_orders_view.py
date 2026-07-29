"""
Purchase Orders View
List, filter, inspect, and update purchase order status.
"""

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path

from src.services.purchase_order_service import PurchaseOrderService
from src.ui.list_style_helpers import make_badge


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


class PurchaseOrdersView(ctk.CTkFrame):
    """Frame for purchase order management."""

    def __init__(self, parent, current_user_role: str = ""):
        super().__init__(parent)
        self.purchase_order_service = PurchaseOrderService()
        self.is_admin = (current_user_role or "").lower() == "administrator"
        self.current_orders = []
        self.selected_order_id = None
        self.selected_order_status = None
        self.order_row_frames = {}
        self._setup_ui()
        self._load_orders()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="Purchase Orders", font=("Segoe UI", 19, "bold")).pack(side="left", padx=5)

        self.filter_combo = ctk.CTkComboBox(top_frame, values=["all", "pending", "received"], state="readonly", width=140)
        self.filter_combo.pack(side="right", padx=5)
        self.filter_combo.set("all")
        self.filter_combo.configure(command=lambda _: self._load_orders())

        ctk.CTkButton(top_frame, text="Refresh", width=100, fg_color="gray", command=self._load_orders).pack(
            side="right", padx=5
        )
        self.export_audit_button = ctk.CTkButton(
            top_frame,
            text="Export Audit CSV",
            width=140,
            state="disabled",
            fg_color="gray",
            command=self._export_audit_csv,
        )
        self.export_audit_button.pack(side="right", padx=5)

        self.status_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 14), text_color="gray")
        self.status_label.pack(anchor="w", padx=14, pady=(0, 8))

        self.orders_frame = ctk.CTkScrollableFrame(self, width=1120, height=360)
        self.orders_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self._render_orders_header()

        details_title = ctk.CTkLabel(self, text="Order Items", font=("Arial", 13, "bold"))
        details_title.pack(anchor="w", padx=14, pady=(6, 4))

        self.details_frame = ctk.CTkScrollableFrame(self, width=1120, height=180)
        self.details_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _render_orders_header(self):
        header = ctk.CTkFrame(self.orders_frame, fg_color="gray20", height=35)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)

        columns = [
            ("PO #", 60),
            ("Supplier", 170),
            ("Order Date", 110),
            ("Expected", 110),
            ("Actual", 110),
            ("Status", 90),
            ("Total", 90),
            ("Items", 60),
            ("Actions", 390),
        ]
        for label, width in columns:
            ctk.CTkLabel(header, text=label, width=width, font=("Segoe UI", 12, "bold")).pack(side="left", padx=3)

    def _load_orders(self):
        for widget in self.orders_frame.winfo_children()[1:]:
            widget.destroy()
        self.order_row_frames = {}

        status = self.filter_combo.get()
        self.current_orders = self.purchase_order_service.get_purchase_orders(status=status)
        self.status_label.configure(
            text=f"Showing {len(self.current_orders)} orders ({status}). Click 'View Items' to enable audit export.",
            text_color="gray",
        )

        if not self.current_orders:
            ctk.CTkLabel(self.orders_frame, text="No purchase orders found.", text_color="gray").pack(pady=20)
            self.selected_order_id = None
            self.selected_order_status = None
            self._clear_details()
            return

        for idx, order in enumerate(self.current_orders):
            self._add_order_row(order, idx % 2 == 0)

        current_order_ids = {order.get("id") for order in self.current_orders}
        if self.selected_order_id in current_order_ids:
            self._highlight_selected_order_row()
            self.export_audit_button.configure(state="normal", fg_color="#1f6aa5")
        else:
            self.selected_order_id = None
            self.selected_order_status = None
            self._clear_details()

    def _add_order_row(self, order: dict, alternate: bool):
        bg_color = "#111b2e" if alternate else "#0d1727"
        row = ctk.CTkFrame(self.orders_frame, fg_color=bg_color, height=35)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)
        order_id = order.get("id")
        self.order_row_frames[order_id] = {"frame": row, "default_color": bg_color}

        values = [
            (str(order.get("id")), 60),
            (f"🏭 {(order.get('supplier_name') or 'Unknown')[:22]}", 170),
            (self._fmt_date(order.get("order_date")), 110),
            (self._fmt_date(order.get("expected_delivery_date")), 110),
            (self._fmt_date(order.get("actual_delivery_date")), 110),
            (self._fmt_amount(order.get("total_amount")), 90),
            (str(order.get("item_count") or 0), 60),
        ]
        for idx, (text, width) in enumerate(values):
            if idx == 5:
                make_badge(row, text, "#1e293b", "#cbd5e1", width).pack(side="left", padx=3)
            else:
                ctk.CTkLabel(row, text=text, width=width, font=("Segoe UI", 12)).pack(side="left", padx=3)

        status = ((order.get("status") or "").title()) or "-"
        status_lower = status.lower()
        status_bg = "#0f766e" if status_lower == "received" else "#6d28d9" if status_lower == "pending" else "#334155"
        status_fg = "#d1fae5" if status_lower == "received" else "#e9d5ff"
        make_badge(row, status, status_bg, status_fg, 90).pack(side="left", padx=3)

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="left", padx=3)

        ctk.CTkButton(
            actions,
            text="👁",
            width=90,
            fg_color="#1f6aa5",
            command=lambda po_id=order.get("id"), po_status=(order.get("status") or ""): self._show_order_items(
                po_id, po_status
            ),
        ).pack(side="left", padx=3)

        is_received = (order.get("status") or "").lower() == "received"
        ctk.CTkButton(
            actions,
            text="✓ Received",
            width=120,
            fg_color="green" if not is_received else "gray",
            state="disabled" if is_received else "normal",
            command=lambda po_id=order.get("id"): self._mark_received(po_id),
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            actions,
            text="🗑 Delete",
            width=110,
            fg_color="red" if (not is_received and self.is_admin) else "gray",
            state="disabled" if (is_received or not self.is_admin) else "normal",
            command=lambda po_id=order.get("id"): self._delete_purchase_order(po_id),
        ).pack(side="left", padx=3)

    def _show_order_items(self, purchase_order_id: int, order_status: str = ""):
        self.selected_order_id = purchase_order_id
        self.selected_order_status = (order_status or "").lower()
        self._clear_details()
        self._highlight_selected_order_row()
        self.export_audit_button.configure(state="normal", fg_color="#1f6aa5")

        items = self.purchase_order_service.get_purchase_order_items(purchase_order_id)
        if not items:
            ctk.CTkLabel(self.details_frame, text="No line items in this order.", text_color="gray").pack(pady=15)
            return

        header = ctk.CTkFrame(self.details_frame, fg_color="gray20", height=32)
        header.pack(fill="x", padx=5, pady=3)
        header.pack_propagate(False)
        columns = [
            ("Item", 200),
            ("Barcode", 120),
            ("Qty Ordered", 95),
            ("Qty Received", 95),
            ("Unit £", 90),
            ("Line £", 90),
            ("Actions", 190),
        ]
        for text, width in columns:
            ctk.CTkLabel(header, text=text, width=width, font=("Segoe UI", 11, "bold")).pack(side="left", padx=3)

        for idx, item in enumerate(items):
            row = ctk.CTkFrame(self.details_frame, fg_color="#111b2e" if idx % 2 == 0 else "#0d1727", height=30)
            row.pack(fill="x", padx=5, pady=1)
            row.pack_propagate(False)
            values = [
                ((item.get("item_name") or f"Item {item.get('item_id')}")[:28], 200),
                ((item.get("barcode") or "-")[:18], 120),
                (str(item.get("quantity_ordered") or 0), 95),
                (str(item.get("quantity_received") or 0), 95),
                (self._fmt_amount(item.get("unit_price")), 90),
                (self._fmt_amount(item.get("line_total")), 90),
            ]
            for value_index, (text, width) in enumerate(values):
                if value_index in (2, 3):
                    make_badge(row, text, "#0f766e", "#d1fae5", width).pack(side="left", padx=3)
                else:
                    ctk.CTkLabel(row, text=text, width=width, font=("Segoe UI", 11)).pack(side="left", padx=3)

            action_frame = ctk.CTkFrame(row, fg_color="transparent")
            action_frame.pack(side="left", padx=3)
            is_received = self.selected_order_status == "received"
            ctk.CTkButton(
                action_frame,
                text="✎",
                width=80,
                fg_color="#1f6aa5" if not is_received else "gray",
                state="disabled" if is_received else "normal",
                command=lambda po_item=item: self._edit_order_item(po_item),
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                action_frame,
                text="🗑",
                width=90,
                fg_color="red" if (not is_received and self.is_admin) else "gray",
                state="disabled" if (is_received or not self.is_admin) else "normal",
                command=lambda po_item=item: self._delete_order_item(po_item),
            ).pack(side="left", padx=2)

        self._render_audit_trail(purchase_order_id)

    def _mark_received(self, purchase_order_id: int):
        success, message = self.purchase_order_service.mark_received(purchase_order_id)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        self._load_orders()
        if success:
            self._show_order_items(purchase_order_id, "received")

    def _prompt_admin_password(self):
        dialog = AdminPasswordDialog(self)
        dialog.wait_window()
        return dialog.result

    def _edit_order_item(self, item: dict):
        password = self._prompt_admin_password()
        if password is None:
            self.status_label.configure(text="Edit cancelled.", text_color="gray")
            return

        qty_dialog = ctk.CTkInputDialog(
            text="Enter new ordered quantity:",
            title="Edit PO Item Quantity",
        )
        qty_value = qty_dialog.get_input()
        if qty_value is None:
            self.status_label.configure(text="Edit cancelled.", text_color="gray")
            return

        try:
            new_qty = int(qty_value)
        except ValueError:
            self.status_label.configure(text="Quantity must be a whole number.", text_color="red")
            return

        success, message = self.purchase_order_service.update_purchase_order_item(item.get("id"), new_qty, password)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success and self.selected_order_id:
            self._load_orders()
            self._show_order_items(self.selected_order_id, self.selected_order_status or "")

    def _delete_order_item(self, item: dict):
        if not self.is_admin:
            self.status_label.configure(text="Only administrators can delete transaction records.", text_color="red")
            return

        password = self._prompt_admin_password()
        if password is None:
            self.status_label.configure(text="Delete cancelled.", text_color="gray")
            return

        success, message = self.purchase_order_service.delete_purchase_order_item(item.get("id"), password)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success and self.selected_order_id:
            self._load_orders()
            self._show_order_items(self.selected_order_id, self.selected_order_status or "")

    def _delete_purchase_order(self, purchase_order_id: int):
        if not self.is_admin:
            self.status_label.configure(text="Only administrators can delete transaction records.", text_color="red")
            return

        password = self._prompt_admin_password()
        if password is None:
            self.status_label.configure(text="Delete purchase order cancelled.", text_color="gray")
            return

        success, message = self.purchase_order_service.delete_purchase_order(purchase_order_id, password)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            if self.selected_order_id == purchase_order_id:
                self.selected_order_id = None
                self.selected_order_status = None
                self._clear_details()
            self._load_orders()

    def _clear_details(self):
        for widget in self.details_frame.winfo_children():
            widget.destroy()
        self.export_audit_button.configure(state="disabled", fg_color="gray")

    def _highlight_selected_order_row(self):
        for order_id, row_data in self.order_row_frames.items():
            is_selected = order_id == self.selected_order_id
            row_data["frame"].configure(fg_color="#2f5b85" if is_selected else row_data["default_color"])

    def _render_audit_trail(self, purchase_order_id: int):
        trail = self.purchase_order_service.get_purchase_order_item_audit(purchase_order_id, limit=20)
        if not trail:
            return

        ctk.CTkLabel(
            self.details_frame,
            text="Amendment Audit Trail (latest 20)",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=5, pady=(12, 4))

        header = ctk.CTkFrame(self.details_frame, fg_color="gray20", height=30)
        header.pack(fill="x", padx=5, pady=2)
        header.pack_propagate(False)
        columns = [("When", 130), ("Admin", 120), ("Action", 80), ("Reason", 180), ("Before", 220), ("After", 220)]
        for text, width in columns:
            ctk.CTkLabel(header, text=text, width=width, font=("Segoe UI", 12, "bold")).pack(side="left", padx=3)

        for idx, row_data in enumerate(trail):
            row = ctk.CTkFrame(self.details_frame, fg_color="#111b2e" if idx % 2 == 0 else "#0d1727", height=28)
            row.pack(fill="x", padx=5, pady=1)
            row.pack_propagate(False)

            values = [
                (self._fmt_datetime(row_data.get("changed_at")), 130),
                ((row_data.get("changed_by_username") or "-")[:20], 120),
                ((row_data.get("action") or "-")[:12], 80),
                ((row_data.get("change_reason") or "-")[:28], 180),
                ((row_data.get("old_values") or "-")[:36], 220),
                ((row_data.get("new_values") or "-")[:36], 220),
            ]
            for text, width in values:
                ctk.CTkLabel(row, text=text, width=width, font=("Segoe UI", 12)).pack(side="left", padx=3)

    def _export_audit_csv(self):
        if not self.selected_order_id:
            self.status_label.configure(text="Select an order and click 'View Items' before exporting audit CSV.", text_color="red")
            return

        default_name = f"purchase_order_{self.selected_order_id}_audit.csv"
        output = filedialog.asksaveasfilename(
            title="Export Audit Trail CSV",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv")],
        )
        if not output:
            self.status_label.configure(text="Audit CSV export cancelled.", text_color="gray")
            return

        success, message = self.purchase_order_service.export_purchase_order_item_audit_csv(
            self.selected_order_id, Path(output)
        )
        self.status_label.configure(
            text=f"Audit CSV saved: {message}" if success else message,
            text_color="green" if success else "red",
        )

    @staticmethod
    def _fmt_date(value):
        if not value:
            return "-"
        if hasattr(value, "strftime"):
            return value.strftime("%d-%m-%Y")
        text = str(value)
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            return f"{text[8:10]}-{text[5:7]}-{text[0:4]}"
        return text

    @staticmethod
    def _fmt_amount(value):
        if value is None:
            return "-"
        return f"£{float(value):.2f}"

    @staticmethod
    def _fmt_datetime(value):
        if not value:
            return "-"
        text = str(value)
        if len(text) >= 19 and text[4] == "-" and text[7] == "-":
            return f"{text[8:10]}-{text[5:7]}-{text[0:4]} {text[11:16]}"
        return text
