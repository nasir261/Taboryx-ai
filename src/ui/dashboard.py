"""
Dashboard
Main application dashboard after login
"""

import customtkinter as ctk
import logging
from typing import Callable
from collections import defaultdict
from datetime import date, timedelta
from src.models.models import User
from src.services.inventory_service import InventoryService
from src.config import LABEL_FONT, TITLE_FONT
from src.ui.wifi_manager_view import WiFiManagerView
from src.ui.update_manager_view import UpdateManagerView

logger = logging.getLogger(__name__)


class Dashboard(ctk.CTkFrame):
    """Main dashboard frame"""

    def __init__(self, parent, user: User, logout_callback: Callable):
        super().__init__(parent)
        self.parent = parent
        self.user = user
        self.logout_callback = logout_callback
        self.inventory_service = InventoryService()
        self.time_sync_service = None
        self.current_time_label = None
        self._current_time_job = None
        
        self._create_widgets()
        self._load_dashboard_data()
        self._schedule_current_time_update()
        self._schedule_update_check()

    def _create_widgets(self):
        """Create modern desktop dashboard layout."""
        self.configure(fg_color="#081326")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.nav_buttons = {}

        sidebar = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color="#0b1a33")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=14, pady=(14, 10))
        ctk.CTkLabel(brand, text="Taboryx AI", font=("Segoe UI", 23, "bold"), text_color="#6ee7ff").pack(anchor="w")
        ctk.CTkLabel(brand, text="Pharmacy Inventory System", font=("Segoe UI", 13), text_color="#8fa2c9").pack(anchor="w")

        nav_scroll = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        nav_scroll.pack(fill="both", expand=True, padx=10, pady=(2, 8))
        self._add_sidebar_section(nav_scroll, "Overview", [("Dashboard", self._show_dashboard)])
        self._add_sidebar_section(nav_scroll, "Inventory", [
            ("Inventory", self._show_inventory),
            ("Batches", self._show_batches),
            ("Stock Movements", self._show_movements),
            ("Purchase Orders", self._show_purchase_orders),
            ("Suppliers", self._show_suppliers),
            ("Transfers", self._show_transfers),
        ])
        self._add_sidebar_section(nav_scroll, "Clinical", [
            ("Rooms", self._show_rooms),
            ("Fridges", self._show_fridges),
            ("Audits", self._show_audits),
            ("Barcode Scanner", self._show_barcode_scanner),
        ])
        self._add_sidebar_section(nav_scroll, "Reports & Intelligence", [
            ("Reports", self._show_reports),
            ("Purchasing", self._show_purchasing),
            ("AI Insights", self._show_ai_insights),
            ("AI Chat", self._show_ai_chat),
            ("Notifications", self._show_notifications),
        ])
        self._add_sidebar_section(nav_scroll, "System", [
            ("Users", self._show_users),
            ("Sites", self._show_sites),
            ("Wi-Fi", self._show_wifi_manager),
            ("Updates", self._show_update_manager),
            ("Backup", self._show_backup),
            ("Microphone", self._show_microphone),
        ])

        ctk.CTkButton(sidebar, text="Logout", fg_color="#334155", hover_color="#475569", command=self._logout).pack(
            fill="x", padx=12, pady=(0, 12)
        )

        main = ctk.CTkFrame(self, fg_color="#081326")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        topbar = ctk.CTkFrame(main, fg_color="#0f1d37", height=58)
        topbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        topbar.grid_columnconfigure(0, weight=1)
        topbar.grid_columnconfigure(1, weight=0)

        self.search_entry = ctk.CTkEntry(
            topbar,
            placeholder_text="Search medicine, batch, supplier, or scan barcode...",
            height=36,
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(12, 8), pady=10)

        right_actions = ctk.CTkFrame(topbar, fg_color="transparent")
        right_actions.grid(row=0, column=1, padx=(0, 10))
        ctk.CTkButton(right_actions, text="Scan", width=70, fg_color="#1d4ed8", command=self._show_barcode_scanner).pack(side="left", padx=4)
        self.current_time_label = ctk.CTkLabel(right_actions, text="Current time: --", font=LABEL_FONT, text_color="#93c5fd")
        self.current_time_label.pack(side="left", padx=8)
        self.time_sync_label = ctk.CTkLabel(right_actions, text="Computer time: active", font=LABEL_FONT, text_color="lightgreen")
        self.time_sync_label.pack(side="left", padx=8)
        self.mobile_access_label = ctk.CTkLabel(right_actions, text="Mobile LAN: starting...", font=LABEL_FONT, text_color="#fbbf24")
        self.mobile_access_label.pack(side="left", padx=8)
        self.session_timer_label = ctk.CTkLabel(right_actions, text="Session timeout: --:--", font=LABEL_FONT, text_color="orange")
        self.session_timer_label.pack(side="left", padx=8)

        self.session_warning_label = ctk.CTkLabel(main, text="", font=LABEL_FONT, text_color="#fca5a5")
        self.session_warning_label.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 4))

        self.info_frame = ctk.CTkFrame(main, fg_color="#081326")
        self.info_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.info_frame.grid_columnconfigure(0, weight=1)

        self._set_active_nav("Dashboard")

    def _add_sidebar_section(self, parent, title: str, entries):
        ctk.CTkLabel(parent, text=title.upper(), font=("Segoe UI", 13, "bold"), text_color="#8fa2c9").pack(anchor="w", pady=(10, 4))
        for label, callback in entries:
            button = ctk.CTkButton(
                parent,
                text=label,
                anchor="w",
                height=34,
                fg_color="transparent",
                hover_color="#1b2a46",
                text_color="#dbeafe",
                command=lambda tab=label, cb=callback: self._activate_and_open(tab, cb),
            )
            button.pack(fill="x", pady=2)
            self.nav_buttons[label] = button

    def _activate_and_open(self, tab_name: str, callback):
        self._set_active_nav(tab_name)
        callback()

    def _set_active_nav(self, tab_name: str):
        for name, button in self.nav_buttons.items():
            is_active = name == tab_name
            button.configure(
                fg_color="#2563eb" if is_active else "transparent",
                text_color="#ffffff" if is_active else "#dbeafe",
            )

    def _clear_info_frame(self):
        for widget in self.info_frame.winfo_children():
            widget.destroy()

    def _create_metric_card(self, parent, title: str, value: str, subtitle: str, color: str):
        card = ctk.CTkFrame(parent, fg_color="#0f1d37", corner_radius=10)
        ctk.CTkLabel(card, text=title, text_color=color, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        ctk.CTkLabel(card, text=value, text_color="#f8fafc", font=("Segoe UI", 25, "bold")).pack(anchor="w", padx=12)
        ctk.CTkLabel(card, text=subtitle, text_color="#8fa2c9", font=("Segoe UI", 13)).pack(anchor="w", padx=12, pady=(2, 10))
        return card

    def _build_stock_value_series(self, days: int = 30):
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        timeline = [start_date + timedelta(days=offset) for offset in range(days)]
        day_changes = {day: 0.0 for day in timeline}

        current_total = float(self.inventory_service.get_total_inventory_value() or 0.0)
        all_items = self.inventory_service.get_all_items()
        unit_price_by_item = {item.id: float(item.purchase_price or 0.0) for item in all_items if item.id}

        movements = self.inventory_service.get_stock_movements(limit=4000)
        for movement in movements:
            movement_date = movement.movement_date
            if not movement_date or movement_date < start_date or movement_date > end_date:
                continue
            unit_price = unit_price_by_item.get(movement.item_id, 0.0)
            day_changes[movement_date] += float(movement.quantity_change or 0) * unit_price

        values_by_date = {}
        running = current_total
        for day in reversed(timeline):
            values_by_date[day] = max(0.0, running)
            running -= day_changes.get(day, 0.0)

        labels = [f"{day.day} {day.strftime('%b')}" for day in timeline]
        values = [values_by_date[day] for day in timeline]
        return labels, values

    def _render_stock_trend_chart(self, parent):
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except Exception as e:
            logger.error(f"Trend chart dependencies unavailable: {e}")
            ctk.CTkLabel(parent, text="Trend chart unavailable on this runtime.", text_color="#8fa2c9").pack(
                anchor="w", padx=12, pady=6
            )
            return

        labels, values = self._build_stock_value_series(days=31)
        if not values:
            ctk.CTkLabel(parent, text="No stock value trend data available.", text_color="#8fa2c9").pack(
                anchor="w", padx=12, pady=6
            )
            return

        from matplotlib.ticker import FuncFormatter

        figure = Figure(figsize=(6.2, 2.6), dpi=100)
        figure.patch.set_facecolor("#0f1d37")
        ax = figure.add_subplot(111)
        ax.set_facecolor("#0f1d37")
        ax.plot(values, color="#22d3ee", linewidth=2.2)
        ax.fill_between(range(len(values)), values, [0] * len(values), color="#0ea5a555")
        ax.set_xlim(0, len(values) - 1)
        ax.set_ylim(bottom=0)
        ax.grid(color="#1f2f4f", linewidth=0.6, alpha=0.6)
        ax.tick_params(axis="x", colors="#94a3b8", labelsize=8)
        ax.tick_params(axis="y", colors="#94a3b8", labelsize=8)
        ax.set_xticks(list(range(0, len(labels), 5)))
        ax.set_xticklabels([labels[i] for i in range(0, len(labels), 5)], rotation=0)
        ax.yaxis.set_major_formatter(
            FuncFormatter(lambda y, _pos: f"£{int(y/1000)}k" if y >= 1000 else f"£{int(y)}")
        )
        for spine in ax.spines.values():
            spine.set_color("#1f2f4f")

        canvas = FigureCanvasTkAgg(figure, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(4, 10))

    def _render_category_pie_chart(self, parent, category_values: dict):
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except Exception as e:
            logger.error(f"Pie chart dependencies unavailable: {e}")
            ctk.CTkLabel(parent, text="Pie chart unavailable on this runtime.", text_color="#8fa2c9").pack(
                anchor="w", padx=12, pady=6
            )
            return

        if not category_values:
            ctk.CTkLabel(parent, text="No category data available.", text_color="#8fa2c9").pack(
                anchor="w", padx=12, pady=6
            )
            return

        items = sorted(category_values.items(), key=lambda x: x[1], reverse=True)[:6]
        labels = [name for name, _ in items]
        values = [float(val) for _, val in items]
        total_value = sum(values)
        colors = ["#4F46E5", "#06B6D4", "#22C55E", "#F59E0B", "#EC4899", "#64748B"]

        chart_frame = ctk.CTkFrame(parent, fg_color="transparent")
        chart_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        chart_frame.grid_columnconfigure(0, weight=1)
        chart_frame.grid_columnconfigure(1, weight=1)

        figure = Figure(figsize=(3.2, 2.8), dpi=100)
        figure.patch.set_facecolor("#0f1d37")
        ax = figure.add_subplot(111)
        ax.set_facecolor("#0f1d37")
        wedges, _ = ax.pie(
            values,
            colors=colors[: len(values)],
            startangle=90,
            wedgeprops={"width": 0.42, "edgecolor": "#0f1d37"},
        )
        ax.text(0, 0.05, "Total", ha="center", va="center", color="#94a3b8", fontsize=10)
        ax.text(0, -0.14, f"£{total_value:,.0f}", ha="center", va="center", color="#f8fafc", fontsize=12, fontweight="bold")
        ax.axis("equal")

        canvas = FigureCanvasTkAgg(figure, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        legend = ctk.CTkFrame(chart_frame, fg_color="transparent")
        legend.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        for idx, (name, value) in enumerate(items):
            percent = int(round((value / total_value) * 100)) if total_value > 0 else 0
            row = ctk.CTkFrame(legend, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text="●", text_color=colors[idx], font=("Segoe UI", 15, "bold")).pack(side="left")
            ctk.CTkLabel(row, text=f"{name[:18]}", text_color="#cbd5e1", anchor="w").pack(side="left", padx=(6, 4))
            ctk.CTkLabel(row, text=f"{percent}%  £{value:,.0f}", text_color="#93c5fd").pack(side="right")

    def _load_dashboard_data(self):
        """Load and display modern dashboard data."""
        try:
            self._set_active_nav("Dashboard")
            total_value = self.inventory_service.get_total_inventory_value()
            low_stock_items = self.inventory_service.get_low_stock_items()
            expired_items = self.inventory_service.get_expired_items()
            all_items = self.inventory_service.get_all_items()
            expiring_30 = self.inventory_service.get_expiring_items(30)

            self._clear_info_frame()

            title_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
            title_frame.grid(row=0, column=0, sticky="ew", padx=2, pady=(0, 8))
            title_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(title_frame, text="Dashboard", font=("Segoe UI", 27, "bold"), text_color="#e2e8f0").grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                title_frame,
                text=f"{self.user.full_name}  •  {self.user.role.replace('_', ' ').title()}",
                text_color="#8fa2c9",
                font=("Segoe UI", 14),
            ).grid(row=1, column=0, sticky="w")

            cards = ctk.CTkFrame(self.info_frame, fg_color="transparent")
            cards.grid(row=1, column=0, sticky="ew")
            for i in range(5):
                cards.grid_columnconfigure(i, weight=1)

            card_data = [
                ("Total Stock Value", f"£{total_value:,.2f}", "Real-time stock valuation", "#22d3ee"),
                ("Total Items", str(len(all_items)), "Tracked products", "#60a5fa"),
                ("Low Stock Items", str(len(low_stock_items)), "Below minimum level", "#f59e0b"),
                ("Expired / Near Expiry", str(len(expired_items) + len(expiring_30)), f"{len(expired_items)} expired", "#f43f5e"),
                ("Today Dispensed", str(sum(max(0, item.minimum_quantity - item.current_quantity) for item in low_stock_items)), "Demand indicator", "#a78bfa"),
            ]
            for idx, (title, value, subtitle, color) in enumerate(card_data):
                self._create_metric_card(cards, title, value, subtitle, color).grid(row=0, column=idx, padx=6, pady=4, sticky="nsew")

            main_row = ctk.CTkFrame(self.info_frame, fg_color="transparent")
            main_row.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
            main_row.grid_columnconfigure(0, weight=2)
            main_row.grid_columnconfigure(1, weight=1)

            trend_panel = ctk.CTkFrame(main_row, fg_color="#0f1d37", corner_radius=10)
            trend_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
            ctk.CTkLabel(
                trend_panel,
                text="Stock Trend (Value)",
                font=("Segoe UI", 16, "bold"),
                text_color="#e2e8f0",
            ).pack(anchor="w", padx=12, pady=(10, 6))
            self._render_stock_trend_chart(trend_panel)

            cat_panel = ctk.CTkFrame(main_row, fg_color="#0f1d37", corner_radius=10)
            cat_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
            ctk.CTkLabel(cat_panel, text="Stock by Category", font=("Segoe UI", 16, "bold"), text_color="#e2e8f0").pack(anchor="w", padx=12, pady=(10, 6))
            category_values = defaultdict(float)
            for item in all_items:
                category = item.category or "Other"
                category_values[category] += self.inventory_service.get_item_stock_value(item.id) if item.id else 0.0
            self._render_category_pie_chart(cat_panel, category_values)

            bottom_row = ctk.CTkFrame(self.info_frame, fg_color="transparent")
            bottom_row.grid(row=3, column=0, sticky="ew", pady=(8, 0))
            bottom_row.grid_columnconfigure(0, weight=2)
            bottom_row.grid_columnconfigure(1, weight=1)

            alerts_panel = ctk.CTkFrame(bottom_row, fg_color="#0f1d37", corner_radius=10)
            alerts_panel.grid(row=0, column=0, sticky="ew", padx=(0, 6))
            ctk.CTkLabel(alerts_panel, text="Alerts", font=("Segoe UI", 16, "bold"), text_color="#e2e8f0").pack(anchor="w", padx=12, pady=(10, 6))
            ctk.CTkLabel(alerts_panel, text=f"• Expired items: {len(expired_items)}", text_color="#fda4af", anchor="w").pack(fill="x", padx=12, pady=1)
            ctk.CTkLabel(alerts_panel, text=f"• Expiring in 30 days: {len(expiring_30)}", text_color="#fcd34d", anchor="w").pack(fill="x", padx=12, pady=1)
            ctk.CTkLabel(alerts_panel, text=f"• Low stock below minimum: {len(low_stock_items)}", text_color="#fdba74", anchor="w").pack(fill="x", padx=12, pady=1)

            quick_panel = ctk.CTkFrame(bottom_row, fg_color="#0f1d37", corner_radius=10)
            quick_panel.grid(row=0, column=1, sticky="ew", padx=(6, 0))
            ctk.CTkLabel(quick_panel, text="Quick Actions", font=("Segoe UI", 16, "bold"), text_color="#e2e8f0").pack(anchor="w", padx=12, pady=(10, 6))
            ctk.CTkButton(quick_panel, text="Add New Item", command=self._show_inventory).pack(fill="x", padx=12, pady=3)
            ctk.CTkButton(quick_panel, text="New Purchase Order", command=self._show_purchasing).pack(fill="x", padx=12, pady=3)
            ctk.CTkButton(quick_panel, text="Record Stock Movement", command=self._show_movements).pack(fill="x", padx=12, pady=3)
            ctk.CTkButton(quick_panel, text="Generate Reports", command=self._show_reports).pack(fill="x", padx=12, pady=(3, 10))

        except Exception as e:
            logger.error(f"Error loading dashboard data: {e}")
            self._clear_info_frame()
            ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading dashboard: {str(e)}",
                text_color="red"
            ).pack(pady=20)

    def _show_dashboard(self):
        """Show dashboard view"""
        self._set_active_nav("Dashboard")
        self._load_dashboard_data()

    def _show_inventory(self):
        """Show inventory view"""
        self._set_active_nav("Inventory")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.inventory_list import InventoryListView
            inventory_view = InventoryListView(
                self.info_frame,
                on_item_selected=self._on_inventory_item_selected
            )
            inventory_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing inventory: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading inventory: {str(e)}",
                text_color="red"
            )
            error_label.pack()

    def _on_inventory_item_selected(self, item_id: int):
        """Handle inventory item selection"""
        logger.info(f"Item selected: {item_id}")

    def _show_barcode_scanner(self):
        """Show barcode scanner view"""
        self._set_active_nav("Barcode Scanner")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.barcode_scanner_view import BarcodeScannerView
            scanner_view = BarcodeScannerView(
                self.info_frame,
                on_item_found=self._on_item_scanned
            )
            scanner_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing barcode scanner: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading barcode scanner: {str(e)}",
                text_color="red"
            )
            error_label.pack()

    def _show_microphone(self):
        """Show microphone settings and diagnostics view"""
        self._set_active_nav("Microphone")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.microphone_settings_view import MicrophoneSettingsView
            microphone_view = MicrophoneSettingsView(self.info_frame)
            microphone_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing microphone settings: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading microphone settings: {str(e)}",
                text_color="red"
            )
            error_label.pack()

    def _on_item_scanned(self, item):
        """Handle scanned item"""
        logger.info(f"Item scanned: {item.item_name}")

    def _show_rooms(self):
        """Show clinical rooms view"""
        self._set_active_nav("Rooms")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.clinical_rooms_view import ClinicalRoomsView
            rooms_view = ClinicalRoomsView(self.info_frame)
            rooms_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing rooms: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading rooms: {str(e)}",
                text_color="red"
            )
            error_label.pack()

    def _show_fridges(self):
        """Show fridge monitoring view."""
        self._set_active_nav("Fridges")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.fridge_monitoring_view import FridgeMonitoringView
            fridges_view = FridgeMonitoringView(self.info_frame)
            fridges_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing fridge monitoring: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading fridge monitoring: {str(e)}",
                text_color="red"
            )
            error_label.pack()

    def _show_batches(self):
        """Show stock batches view"""
        self._set_active_nav("Batches")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.stock_batches_view import StockBatchesView
            batches_view = StockBatchesView(self.info_frame)
            batches_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing stock batches: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading stock batches: {str(e)}",
                text_color="red"
            )
            error_label.pack()

    def _show_sites(self):
        """Show site management view for administrators."""
        self._set_active_nav("Sites")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        if (self.user.role or "").lower() != "administrator":
            ctk.CTkLabel(
                self.info_frame,
                text="Only administrators can access site management.",
                text_color="red",
            ).pack(pady=20)
            return

        try:
            from src.ui.sites_view import SitesView

            sites_view = SitesView(self.info_frame)
            sites_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing sites: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading sites: {str(e)}",
                text_color="red"
            )
            error_label.pack()

    def _show_audits(self):
        """Show room audits view"""
        self._set_active_nav("Audits")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.room_audits_view import RoomAuditsView
            audits_view = RoomAuditsView(
                self.info_frame,
                current_user_id=self.user.id,
                current_user_role=self.user.role,
            )
            audits_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing audits: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading audits: {str(e)}",
                text_color="red"
            )
            error_label.pack()

    def _show_transfers(self):
        """Show stock transfers view"""
        self._set_active_nav("Transfers")
        for widget in self.info_frame.winfo_children():
            widget.destroy()
 
        try:
            from src.ui.stock_transfers_view import StockTransfersView
            transfers_view = StockTransfersView(self.info_frame, current_user_id=self.user.id)
            transfers_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing transfers: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading transfers: {str(e)}",
                text_color="red"
            )
            error_label.pack()
 
    def _show_reports(self):
        """Show reports view"""
        self._set_active_nav("Reports")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.reporting_view import ReportingView

            reporting_view = ReportingView(self.info_frame)
            reporting_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing reports: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading reports: {str(e)}",
                text_color="red",
            )
            error_label.pack()

    def _show_purchasing(self):
        """Show purchasing recommendations view"""
        self._set_active_nav("Purchasing")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.purchasing_view import PurchasingView

            purchasing_view = PurchasingView(
                self.info_frame,
                current_user_id=self.user.id,
                current_user_role=self.user.role,
            )
            purchasing_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing purchasing: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading purchasing: {str(e)}",
                text_color="red",
            )
            error_label.pack()

    def _show_purchase_orders(self):
        """Show purchase orders management view"""
        self._set_active_nav("Purchase Orders")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.purchase_orders_view import PurchaseOrdersView

            purchase_orders_view = PurchaseOrdersView(self.info_frame, current_user_role=self.user.role)
            purchase_orders_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing purchase orders: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading purchase orders: {str(e)}",
                text_color="red",
            )
            error_label.pack()

    def _show_update_manager(self):
        """Show admin-only software update manager view."""
        self._set_active_nav("Updates")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        if (self.user.role or "").lower() not in {"administrator", "admin"}:
            ctk.CTkLabel(
                self.info_frame,
                text="Only administrators can manage software updates.",
                text_color="red",
            ).pack(pady=20)
            return

        try:
            update_view = UpdateManagerView(self.info_frame, user_role=self.user.role)
            update_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing update manager: {e}")
            ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading update manager: {str(e)}",
                text_color="red",
            ).pack()

    def _schedule_update_check(self):
        """Run a background update check shortly after dashboard loads and push a notification if found."""
        import threading
        from src.services.update_service import UpdateService

        def _worker():
            try:
                svc = UpdateService()
                available, manifest, _err = svc.check_for_update(timeout=8)
                if available and manifest:
                    latest = manifest.get("version", "?")
                    self.after(0, lambda: self._show_update_notification(latest))
            except Exception as exc:
                logger.debug("Background update check failed silently: %s", exc)

        threading.Thread(target=_worker, daemon=True).start()

    def _show_update_notification(self, latest_version: str):
        """Flash an update badge on the Updates sidebar button."""
        btn = self.nav_buttons.get("Updates")
        if btn:
            btn.configure(
                text=f"Updates  ●",
                text_color="#fcd34d",
                fg_color="#7c3800",
            )
        # Also surface it in the top bar temporarily
        try:
            self.mobile_access_label.configure(
                text=f"Update available: v{latest_version}  →  System › Updates",
                text_color="#fcd34d",
            )
        except Exception:
            pass

    def _show_wifi_manager(self):
        """Show admin-only Wi-Fi connection management view."""
        self._set_active_nav("Wi-Fi")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        if (self.user.role or "").lower() not in {"administrator", "admin"}:
            ctk.CTkLabel(
                self.info_frame,
                text="Only administrators can manage Wi-Fi connections.",
                text_color="red",
            ).pack(pady=20)
            return

        try:
            wifi_view = WiFiManagerView(self.info_frame, user_role=self.user.role)
            wifi_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing Wi-Fi manager: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading Wi-Fi manager: {str(e)}",
                text_color="red",
            )
            error_label.pack()

    def _show_backup(self):
        """Show backup and restore view."""
        self._set_active_nav("Backup")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.backup_view import BackupView

            backup_view = BackupView(self.info_frame)
            backup_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing backup view: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading backup view: {str(e)}",
                text_color="red",
            )
            error_label.pack()

    def _show_notifications(self):
        """Show notifications center view."""
        self._set_active_nav("Notifications")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.notifications_view import NotificationsView

            notifications_view = NotificationsView(self.info_frame)
            notifications_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing notifications view: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading notifications view: {str(e)}",
                text_color="red",
            )
            error_label.pack()

    def _show_ai_insights(self):
        """Show AI insights view."""
        self._set_active_nav("AI Insights")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.ai_insights_view import AIInsightsView

            insights_view = AIInsightsView(self.info_frame)
            insights_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing AI insights: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading AI insights: {str(e)}",
                text_color="red",
            )
            error_label.pack()

    def _show_ai_chat(self):
        """Show AI chat assistant view."""
        self._set_active_nav("AI Chat")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.ai_chat_view import AIChatView

            chat_view = AIChatView(self.info_frame)
            chat_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing AI chat: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading AI chat: {str(e)}",
                text_color="red",
            )
            error_label.pack()

    def _show_users(self):
        """Show user management view for administrators."""
        self._set_active_nav("Users")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        if (self.user.role or "").lower() != "administrator":
            ctk.CTkLabel(
                self.info_frame,
                text="Only administrators can access user management.",
                text_color="red",
            ).pack(pady=20)
            return

        try:
            from src.ui.user_management_view import UserManagementView

            users_view = UserManagementView(self.info_frame)
            users_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing user management: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading user management: {str(e)}",
                text_color="red",
            )
            error_label.pack()
 
    def _show_suppliers(self):
        """Show suppliers management view"""
        self._set_active_nav("Suppliers")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.suppliers_view import SuppliersView
            suppliers_view = SuppliersView(self.info_frame)
            suppliers_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing suppliers: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading suppliers: {str(e)}",
                text_color="red"
            )
            error_label.pack()

    def _show_movements(self):
        """Show stock movements view"""
        self._set_active_nav("Stock Movements")
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        try:
            from src.ui.stock_movements_view import StockMovementsView
            movements_view = StockMovementsView(
                self.info_frame,
                current_user_id=self.user.id,
                on_movement_recorded=self._load_dashboard_data
            )
            movements_view.pack(fill="both", expand=True)
        except Exception as e:
            logger.error(f"Error showing movements: {e}")
            error_label = ctk.CTkLabel(
                self.info_frame,
                text=f"Error loading movements: {str(e)}",
                text_color="red"
            )
            error_label.pack()

    def _logout(self):
        """Handle logout"""
        if self._current_time_job:
            try:
                self.after_cancel(self._current_time_job)
            except Exception:
                pass
            self._current_time_job = None
        self.logout_callback()

    def update_session_timeout(self, seconds_remaining: int):
        minutes = seconds_remaining // 60
        seconds = seconds_remaining % 60
        timer_color = "orange" if seconds_remaining > 60 else "red"
        self.session_timer_label.configure(
            text=f"Session timeout: {minutes:02d}:{seconds:02d}",
            text_color=timer_color,
        )

    def set_session_timeout_warning(self, show_warning: bool):
        warning_text = "Auto logout in under 60 seconds due to inactivity." if show_warning else ""
        self.session_warning_label.configure(text=warning_text)

    def update_time_sync_status(self, enabled: bool, offset_seconds: int, last_sync_text: str, status_text: str = ""):
        if not enabled:
            self.time_sync_label.configure(text="Computer time: enabled", text_color="lightgreen")
            return

        base = "Computer time: active"
        if last_sync_text:
            base = f"{base} | last web check {last_sync_text}"
        if status_text:
            base = f"{base} | {status_text}"
        status_lower = (status_text or "").lower()
        if status_lower in {"ok", "pending"} or status_text == "":
            color = "lightgreen"
        elif "temporarily unavailable" in status_lower:
            color = "orange"
        else:
            color = "red"
        self.time_sync_label.configure(text=base, text_color=color)

    def update_mobile_access_status(self, status_text: str, color: str = "#fbbf24"):
        self.mobile_access_label.configure(text=status_text, text_color=color)

    def _schedule_current_time_update(self):
        self._update_current_time()

    def _update_current_time(self):
        from src.services.time_sync_service import get_time_sync_service

        if self.current_time_label is None:
            return
        if self.time_sync_service is None:
            self.time_sync_service = get_time_sync_service()
        self.current_time_label.configure(text=f"Current time: {self.time_sync_service.get_date_time_signature()}")
        self._current_time_job = self.after(1000, self._update_current_time)
