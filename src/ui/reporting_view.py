"""
Reporting View
UI for generating inventory and stock movement reports
"""

import customtkinter as ctk
from tkinter import filedialog
import logging
from pathlib import Path
from typing import Optional
from src.services.reporting_service import ReportingService
from src.ui.list_style_helpers import make_badge

logger = logging.getLogger(__name__)


class ReportingView(ctk.CTkFrame):
    """Frame for report generation"""

    def __init__(self, parent):
        super().__init__(parent)
        self.reporting_service = ReportingService()
        self._setup_ui()

    def _setup_ui(self):
        """Create UI elements for report generation"""
        title = ctk.CTkLabel(self, text="Reports", font=("Segoe UI", 19, "bold"))
        title.pack(pady=20)

        description = ctk.CTkLabel(
            self,
            text="Generate inventory and stock movement reports in CSV, Excel, or PDF formats.",
            font=("Segoe UI", 15),
            text_color="gray",
        )
        description.pack(pady=5)

        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(button_frame, text="Inventory Reports", font=("Segoe UI", 15, "bold")).pack(
            anchor="w", pady=(0, 10)
        )

        report_buttons = [
            ("Export Inventory CSV", self._export_inventory_csv),
            ("Export Inventory Excel", self._export_inventory_excel),
            ("Export Inventory PDF", self._export_inventory_pdf),
        ]

        for label, command in report_buttons:
            ctk.CTkButton(button_frame, text=f"📄 {label}", width=220, command=command).pack(
                side="left", padx=10, pady=5
            )

        ctk.CTkLabel(button_frame, text="Stock Movement Reports", font=("Segoe UI", 15, "bold")).pack(
            anchor="w", pady=(20, 10)
        )

        movement_buttons = [
            ("Export Movements CSV", self._export_movements_csv),
            ("Export Movements Excel", self._export_movements_excel),
            ("Export Movements PDF", self._export_movements_pdf),
        ]

        for label, command in movement_buttons:
            ctk.CTkButton(button_frame, text=f"📄 {label}", width=220, command=command).pack(
                side="left", padx=10, pady=5
            )

        self.status_label = ctk.CTkLabel(self, text="Ready to generate reports.", font=("Segoe UI", 14), text_color="gray")
        self.status_label.pack(pady=20)

    def _choose_save_path(self, default_path: Path, filetypes: list) -> Optional[Path]:
        path = filedialog.asksaveasfilename(
            title="Save Report",
            defaultextension=default_path.suffix,
            initialfile=default_path.name,
            filetypes=filetypes,
        )
        return Path(path) if path else None

    def _set_status(self, message: str, success: bool = True):
        color = "green" if success else "red"
        self.status_label.configure(text=message, text_color=color)
        logger.info(message)

    def _export_inventory_csv(self):
        default_path = self.reporting_service._default_filename("inventory_report", "csv")
        path = self._choose_save_path(default_path, [("CSV files", "*.csv")])
        if not path:
            return

        success, message = self.reporting_service.generate_inventory_csv(path)
        self._set_status(f"Inventory CSV saved: {message}" if success else message, success)

    def _export_inventory_excel(self):
        default_path = self.reporting_service._default_filename("inventory_report", "xlsx")
        path = self._choose_save_path(default_path, [("Excel files", "*.xlsx")])
        if not path:
            return

        success, message = self.reporting_service.generate_inventory_excel(path)
        self._set_status(f"Inventory Excel saved: {message}" if success else message, success)

    def _export_inventory_pdf(self):
        default_path = self.reporting_service._default_filename("inventory_report", "pdf")
        path = self._choose_save_path(default_path, [("PDF files", "*.pdf")])
        if not path:
            return

        success, message = self.reporting_service.generate_inventory_pdf(path)
        self._set_status(f"Inventory PDF saved: {message}" if success else message, success)

    def _export_movements_csv(self):
        default_path = self.reporting_service._default_filename("stock_movements_report", "csv")
        path = self._choose_save_path(default_path, [("CSV files", "*.csv")])
        if not path:
            return

        success, message = self.reporting_service.generate_movements_csv(path)
        self._set_status(f"Stock movements CSV saved: {message}" if success else message, success)

    def _export_movements_excel(self):
        default_path = self.reporting_service._default_filename("stock_movements_report", "xlsx")
        path = self._choose_save_path(default_path, [("Excel files", "*.xlsx")])
        if not path:
            return

        success, message = self.reporting_service.generate_movements_excel(path)
        self._set_status(f"Stock movements Excel saved: {message}" if success else message, success)

    def _export_movements_pdf(self):
        default_path = self.reporting_service._default_filename("stock_movements_report", "pdf")
        path = self._choose_save_path(default_path, [("PDF files", "*.pdf")])
        if not path:
            return

        success, message = self.reporting_service.generate_movements_pdf(path)
        self._set_status(f"Stock movements PDF saved: {message}" if success else message, success)
