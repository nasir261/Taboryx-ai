"""
AI Insights View
Shows shortage forecasts and expiry risk signals.
"""

import customtkinter as ctk

from src.services.ai_insights_service import AIInsightsService
from src.ui.list_style_helpers import make_badge


class AIInsightsView(ctk.CTkFrame):
    """Frame for AI insights and forecasts."""

    def __init__(self, parent):
        super().__init__(parent)
        self.ai_service = AIInsightsService()
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="AI Insights", font=("Segoe UI", 19, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(top_frame, text="Refresh", width=100, fg_color="gray", command=self._load_data).pack(
            side="right", padx=5
        )

        self.status_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 14), text_color="gray")
        self.status_label.pack(anchor="w", padx=14, pady=(0, 8))

        ctk.CTkLabel(self, text="Usage Forecast & Shortage Risk", font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=14, pady=(4, 4)
        )
        self.forecast_frame = ctk.CTkScrollableFrame(self, width=1120, height=260)
        self.forecast_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(self, text="Expiry Risk (Next 90 Days)", font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=14, pady=(4, 4)
        )
        self.expiry_frame = ctk.CTkScrollableFrame(self, width=1120, height=220)
        self.expiry_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _load_data(self):
        self._render_forecasts(self.ai_service.get_usage_forecasts())
        self._render_expiry_risk(self.ai_service.get_expiry_risk_items(90))
        self.status_label.configure(text="AI insights refreshed.", text_color="green")

    def _render_forecasts(self, rows):
        for widget in self.forecast_frame.winfo_children():
            widget.destroy()

        header = ctk.CTkFrame(self.forecast_frame, fg_color="gray20", height=32)
        header.pack(fill="x", padx=5, pady=3)
        header.pack_propagate(False)
        columns = [
            ("Item", 170),
            ("Current", 80),
            ("Next Month", 95),
            ("Next Quarter", 95),
            ("Next Year", 95),
            ("Confidence", 90),
            ("Shortage Risk", 95),
            ("Action", 180),
        ]
        for text, width in columns:
            ctk.CTkLabel(header, text=text, width=width, font=("Segoe UI", 12, "bold")).pack(side="left", padx=3)

        for i, row_data in enumerate(rows):
            row = ctk.CTkFrame(self.forecast_frame, fg_color="#111b2e" if i % 2 == 0 else "#0d1727", height=30)
            row.pack(fill="x", padx=5, pady=1)
            row.pack_propagate(False)
            values = [
                (f"📈 {row_data['item_name'][:24]}", 170),
                (str(row_data["current_quantity"]), 80),
                (str(row_data["forecast_next_month"]), 95),
                (str(row_data["forecast_next_quarter"]), 95),
                (str(row_data["forecast_next_year"]), 95),
                (row_data["confidence"], 90),
                (row_data["shortage_risk"], 95),
                (row_data["recommended_action"][:28], 180),
            ]
            for idx, (text, width) in enumerate(values):
                if idx in (1, 2, 3, 4):
                    make_badge(row, text, "#1e293b", "#cbd5e1", width).pack(side="left", padx=3)
                elif idx == 5:
                    conf = str(text).lower()
                    bg = "#0f766e" if conf in {"high", "good", "strong"} else "#334155"
                    fg = "#d1fae5" if bg == "#0f766e" else "#e2e8f0"
                    make_badge(row, text, bg, fg, width).pack(side="left", padx=3)
                elif idx == 6:
                    risk = str(text).lower()
                    bg = "#7c2d12" if risk in {"high", "critical"} else "#334155"
                    fg = "#fde68a" if bg == "#7c2d12" else "#e2e8f0"
                    make_badge(row, text, bg, fg, width).pack(side="left", padx=3)
                else:
                    ctk.CTkLabel(row, text=text, width=width, font=("Segoe UI", 12)).pack(side="left", padx=3)

    def _render_expiry_risk(self, rows):
        for widget in self.expiry_frame.winfo_children():
            widget.destroy()

        header = ctk.CTkFrame(self.expiry_frame, fg_color="gray20", height=32)
        header.pack(fill="x", padx=5, pady=3)
        header.pack_propagate(False)
        columns = [("Item", 220), ("Qty", 80), ("Days to Expiry", 120), ("Risk", 90), ("Score", 90), ("Action", 220)]
        for text, width in columns:
            ctk.CTkLabel(header, text=text, width=width, font=("Segoe UI", 12, "bold")).pack(side="left", padx=3)

        for i, row_data in enumerate(rows):
            row = ctk.CTkFrame(self.expiry_frame, fg_color="#111b2e" if i % 2 == 0 else "#0d1727", height=30)
            row.pack(fill="x", padx=5, pady=1)
            row.pack_propagate(False)
            values = [
                (f"💊 {row_data['item_name'][:30]}", 220),
                (str(row_data["current_quantity"]), 80),
                (str(row_data["days_to_expiry"]), 120),
                (row_data["risk_level"], 90),
                (str(row_data["risk_score"]), 90),
                (row_data["action"][:34], 220),
            ]
            for idx, (text, width) in enumerate(values):
                if idx in (1, 2, 4):
                    make_badge(row, text, "#1e293b", "#cbd5e1", width).pack(side="left", padx=3)
                elif idx == 3:
                    risk = str(text).lower()
                    bg = "#7c2d12" if risk in {"high", "critical"} else "#6d28d9" if risk == "medium" else "#0f766e"
                    fg = "#fde68a" if bg == "#7c2d12" else "#e9d5ff" if bg == "#6d28d9" else "#d1fae5"
                    make_badge(row, text, bg, fg, width).pack(side="left", padx=3)
                else:
                    ctk.CTkLabel(row, text=text, width=width, font=("Segoe UI", 12)).pack(side="left", padx=3)
