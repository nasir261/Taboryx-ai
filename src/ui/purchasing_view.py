"""
Purchasing View
Displays purchasing recommendations and stock coverage signals.
"""

import customtkinter as ctk
import tkinter as tk

from src.services.purchasing_service import PurchasingService
from src.services.purchase_order_service import PurchaseOrderService


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


class PurchasingSettingsDialog(ctk.CTkToplevel):
    """Dialog for smart purchasing configuration."""

    def __init__(self, parent, settings: dict):
        super().__init__(parent)
        self.title("Purchasing Settings")
        self.geometry("480x340")
        self.resizable(False, False)
        self.grab_set()
        self.result = None

        form = ctk.CTkFrame(self)
        form.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(form, text="Lookback Days", font=("Arial", 11, "bold")).pack(anchor="w", pady=(8, 2))
        self.lookback_entry = ctk.CTkEntry(form)
        self.lookback_entry.pack(fill="x")
        self.lookback_entry.insert(0, str(settings.get("lookback_days", 90)))

        ctk.CTkLabel(form, text="Safety Stock Factor", font=("Arial", 11, "bold")).pack(anchor="w", pady=(12, 2))
        self.safety_factor_entry = ctk.CTkEntry(form)
        self.safety_factor_entry.pack(fill="x")
        self.safety_factor_entry.insert(0, str(settings.get("safety_stock_factor", 0.5)))

        ctk.CTkLabel(form, text="Minimum Safety Stock", font=("Arial", 11, "bold")).pack(anchor="w", pady=(12, 2))
        self.min_safety_entry = ctk.CTkEntry(form)
        self.min_safety_entry.pack(fill="x")
        self.min_safety_entry.insert(0, str(settings.get("min_safety_stock", 5)))

        ctk.CTkLabel(form, text="Budget Limit (£, optional)", font=("Arial", 11, "bold")).pack(anchor="w", pady=(12, 2))
        self.budget_entry = ctk.CTkEntry(form)
        self.budget_entry.pack(fill="x")
        budget_limit = settings.get("budget_limit")
        if budget_limit is not None:
            self.budget_entry.insert(0, str(budget_limit))

        button_frame = ctk.CTkFrame(form, fg_color="transparent")
        button_frame.pack(fill="x", pady=(18, 0))
        ctk.CTkButton(button_frame, text="Save", width=120, command=self._confirm).pack(side="left", padx=4)
        ctk.CTkButton(button_frame, text="Cancel", width=120, fg_color="gray", command=self._cancel).pack(side="left", padx=4)

    def _confirm(self):
        self.result = {
            "lookback_days": self.lookback_entry.get().strip(),
            "safety_stock_factor": self.safety_factor_entry.get().strip(),
            "min_safety_stock": self.min_safety_entry.get().strip(),
            "budget_limit": self.budget_entry.get().strip(),
        }
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class PurchasingView(ctk.CTkFrame):
    """Frame for purchase recommendations."""

    def __init__(self, parent, current_user_id: int = None, current_user_role: str = ""):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.is_admin = (current_user_role or "").lower() == "administrator"
        self.purchasing_service = PurchasingService()
        self.purchase_order_service = PurchaseOrderService()
        self.current_recommendations = []
        self._setup_ui()
        self._load_recommendations()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="Purchasing Recommendations", font=("Arial", 16, "bold")).pack(
            side="left", padx=5
        )
        ctk.CTkButton(top_frame, text="Refresh", width=100, fg_color="gray", command=self._load_recommendations).pack(
            side="right", padx=5
        )
        ctk.CTkButton(top_frame, text="Settings", width=100, command=self._open_settings).pack(side="right", padx=5)

        self.summary_label = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color="gray")
        self.summary_label.pack(anchor="w", padx=14, pady=(0, 8))

        self.status_label = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color="gray")
        self.status_label.pack(anchor="w", padx=14, pady=(0, 8))
        self.status_label.configure(
            text=(
                "Create PO is enabled for items with an assigned supplier. "
                "When recommendation quantity is zero, you can still enter a manual quantity. "
                "Delete PO requires a pending order and administrator access."
            ),
            text_color="gray",
        )

        self.table_container = ctk.CTkFrame(self)
        self.table_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.table_container.grid_rowconfigure(0, weight=1)
        self.table_container.grid_columnconfigure(0, weight=1)

        self.table_canvas = tk.Canvas(self.table_container, highlightthickness=0, borderwidth=0)
        self.table_canvas.grid(row=0, column=0, sticky="nsew")

        self.y_scrollbar = tk.Scrollbar(self.table_container, orient="vertical", command=self.table_canvas.yview)
        self.y_scrollbar.grid(row=0, column=1, sticky="ns")
        self.x_scrollbar = tk.Scrollbar(self.table_container, orient="horizontal", command=self.table_canvas.xview)
        self.x_scrollbar.grid(row=1, column=0, sticky="ew")

        self.table_canvas.configure(yscrollcommand=self.y_scrollbar.set, xscrollcommand=self.x_scrollbar.set)
        self.table_content = ctk.CTkFrame(self.table_canvas, fg_color="transparent")
        self.table_window = self.table_canvas.create_window((0, 0), window=self.table_content, anchor="nw")
        self.table_content.bind("<Configure>", self._update_table_scrollregion)
        self.table_canvas.bind("<Configure>", self._on_canvas_resized)

        self._render_header()

    def _render_header(self):
        header = ctk.CTkFrame(self.table_content, fg_color="gray20", height=35)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)

        columns = [
            ("Item", 130),
            ("Supplier", 130),
            ("On Hand", 55),
            ("Min", 45),
            ("Max", 45),
            ("Reorder", 65),
            ("Monthly Use", 75),
            ("Lead Days", 65),
            ("Recommended", 75),
            ("Action", 90),
            ("Reason", 165),
            ("PO Actions", 190),
        ]
        for label, width in columns:
            ctk.CTkLabel(header, text=label, width=width, font=("Arial", 10, "bold")).pack(side="left", padx=2)

    def _load_recommendations(self):
        for widget in self.table_content.winfo_children():
            widget.destroy()
        self._render_header()

        settings = self.purchasing_service.get_recommendation_settings()
        self.current_recommendations = self.purchasing_service.get_purchase_recommendations()
        order_now_count = len([rec for rec in self.current_recommendations if rec["action"] == "Order now"])
        order_soon_count = len([rec for rec in self.current_recommendations if rec["action"] == "Order soon"])
        review_budget_count = len([rec for rec in self.current_recommendations if rec["action"] == "Review budget"])
        self.summary_label.configure(
            text=(
                f"Order now: {order_now_count} items | "
                f"Order soon: {order_soon_count} items | "
                f"Review budget: {review_budget_count} items | "
                f"Total tracked: {len(self.current_recommendations)}"
            )
        )
        budget_text = "None" if settings["budget_limit"] is None else f"£{settings['budget_limit']:.2f}"
        self.status_label.configure(
            text=(
                f"Settings - Lookback: {settings['lookback_days']}d, "
                f"Safety factor: {settings['safety_stock_factor']:.2f}, "
                f"Min safety: {settings['min_safety_stock']}, "
                f"Budget: {budget_text}"
            ),
            text_color="gray",
        )

        if not self.current_recommendations:
            ctk.CTkLabel(self.table_content, text="No inventory items found.", font=("Arial", 11), text_color="gray").pack(
                pady=30
            )
            return

        for index, rec in enumerate(self.current_recommendations):
            self._add_row(rec, index % 2 == 0)

    def _add_row(self, rec, alternate: bool):
        bg_color = "gray15" if alternate else "gray10"
        row = ctk.CTkFrame(self.table_content, fg_color=bg_color, height=35)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)

        columns = [
            (rec["item_name"][:18], 130),
            (rec["supplier_name"][:18], 130),
            (str(rec["current_quantity"]), 55),
            (str(rec["minimum_quantity"]), 45),
            (str(rec["maximum_quantity"]), 45),
            (str(rec["reorder_point"]), 65),
            (str(rec["monthly_usage"]), 75),
            (str(rec["lead_time_days"]), 65),
            (str(rec["recommended_qty"]), 75),
            (rec["action"][:14], 90),
            (rec["reason"][:50], 165),
        ]

        for text, width in columns:
            ctk.CTkLabel(row, text=text, width=width).pack(side="left", padx=2)

        action_frame = ctk.CTkFrame(row, fg_color="transparent", width=190)
        action_frame.pack(side="left", padx=2)
        action_frame.pack_propagate(False)

        has_pending_po = bool(rec.get("pending_purchase_order_id"))
        can_create_recommended = (
            rec["recommended_qty"] > 0
            and rec["supplier_name"] != "Unassigned"
            and rec["action"] in {"Order now", "Order soon", "Review budget"}
        )
        can_create_manual = rec["supplier_name"] != "Unassigned" and not has_pending_po
        can_create_po = can_create_recommended or can_create_manual
        ctk.CTkButton(
            action_frame,
            text="Create PO",
            width=88,
            fg_color="green" if can_create_recommended else ("#1f6aa5" if can_create_po else "gray"),
            state="normal" if can_create_po else "disabled",
            command=lambda r=rec, use_manual=not can_create_recommended: self._create_po(r, use_manual_quantity=use_manual),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            action_frame,
            text="Delete PO",
            width=88,
            fg_color="red" if (has_pending_po and self.is_admin) else "gray",
            state="normal" if (has_pending_po and self.is_admin) else "disabled",
            command=lambda r=rec: self._delete_po(r),
        ).pack(side="left", padx=2)

    def _create_po(self, recommendation: dict, use_manual_quantity: bool = False):
        if recommendation.get("pending_purchase_order_id"):
            self.status_label.configure(
                text="This item already has a pending purchase order. Delete it first or mark it received.",
                text_color="red",
            )
            return

        quantity = int(recommendation.get("recommended_qty") or 0)
        if use_manual_quantity or quantity <= 0:
            quantity_input = ctk.CTkInputDialog(
                text=f"Enter order quantity for {recommendation['item_name']}:",
                title="Create Purchase Order",
            ).get_input()
            if quantity_input is None:
                self.status_label.configure(text="Create purchase order cancelled.", text_color="gray")
                return
            try:
                quantity = int(quantity_input.strip())
            except ValueError:
                self.status_label.configure(text="Quantity must be a whole number.", text_color="red")
                return

        if quantity <= 0:
            self.status_label.configure(text="Quantity must be greater than zero.", text_color="red")
            return

        success, message, order_id = self.purchasing_service.create_purchase_order_for_item(
            item_id=recommendation["item_id"],
            quantity=quantity,
            created_by_user_id=self.current_user_id,
            notes=f"Generated from recommendation for {recommendation['item_name']}",
        )
        if success:
            self.status_label.configure(text=f"Created purchase order #{order_id}", text_color="green")
            self._load_recommendations()
        else:
            self.status_label.configure(text=message, text_color="red")

    def _prompt_admin_password(self):
        dialog = AdminPasswordDialog(self)
        dialog.wait_window()
        return dialog.result

    def _delete_po(self, recommendation: dict):
        if not self.is_admin:
            self.status_label.configure(text="Only administrators can delete transaction records.", text_color="red")
            return

        pending_order_id = recommendation.get("pending_purchase_order_id")
        if not pending_order_id:
            self.status_label.configure(text="No pending purchase order available to delete.", text_color="red")
            return

        password = self._prompt_admin_password()
        if password is None:
            self.status_label.configure(text="Delete purchase order cancelled.", text_color="gray")
            return

        success, message = self.purchase_order_service.delete_purchase_order(pending_order_id, password)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_recommendations()

    def _open_settings(self):
        dialog = PurchasingSettingsDialog(self, self.purchasing_service.get_recommendation_settings())
        dialog.wait_window()
        if dialog.result is None:
            return

        try:
            lookback_days = int(dialog.result["lookback_days"])
            safety_stock_factor = float(dialog.result["safety_stock_factor"])
            min_safety_stock = int(dialog.result["min_safety_stock"])
            budget_text = dialog.result["budget_limit"]
            budget_limit = float(budget_text) if budget_text else None
        except ValueError:
            self.status_label.configure(text="Invalid settings values.", text_color="red")
            return

        success, message = self.purchasing_service.update_recommendation_settings(
            lookback_days=lookback_days,
            safety_stock_factor=safety_stock_factor,
            min_safety_stock=min_safety_stock,
            budget_limit=budget_limit,
        )
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_recommendations()

    def _update_table_scrollregion(self, _event=None):
        self.table_canvas.configure(scrollregion=self.table_canvas.bbox("all"))

    def _on_canvas_resized(self, event):
        content_width = self.table_content.winfo_reqwidth()
        self.table_canvas.itemconfigure(self.table_window, width=max(event.width, content_width))
