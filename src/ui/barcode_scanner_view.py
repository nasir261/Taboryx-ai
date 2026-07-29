"""
Barcode Scanner UI
Interactive barcode scanning interface
"""

import customtkinter as ctk
from typing import Optional, Callable
import logging
from src.services.scan_recognition_service import ScanRecognitionService
from src.utils.barcode_scanner import BarcodeScanner
from src.config import CLINICAL_SAFETY_CHECK_NOTICE

logger = logging.getLogger(__name__)


class BarcodeScannerView(ctk.CTkFrame):
    """Frame for barcode scanner operations"""

    def __init__(self, parent, on_item_found: Optional[Callable] = None):
        super().__init__(parent)
        self.scan_recognition_service = ScanRecognitionService()
        self.barcode_scanner = BarcodeScanner(on_barcode_scanned=self._on_barcode_scanned)
        self.on_item_found = on_item_found
        self.last_found_item = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI layout"""
        # Title
        title = ctk.CTkLabel(
            self, text="Barcode / QR Scanner", font=("Arial", 16, "bold")
        )
        title.pack(pady=20)

        # Instructions
        instructions = ctk.CTkLabel(
            self,
            text="Use a USB scanner or enter a barcode / QR code manually below",
            font=("Arial", 11),
            text_color="gray",
        )
        instructions.pack(pady=5)

        ctk.CTkLabel(
            self,
            text=CLINICAL_SAFETY_CHECK_NOTICE,
            wraplength=980,
            justify="left",
            font=("Arial", 10),
            text_color="orange",
        ).pack(pady=(0, 8), padx=20, anchor="w")

        # Barcode input frame
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(input_frame, text="Barcode / QR Code:", font=("Arial", 11, "bold")).pack(
            side="left", padx=5
        )

        self.barcode_entry = ctk.CTkEntry(input_frame, width=300)
        self.barcode_entry.pack(side="left", padx=5)
        self.barcode_entry.bind("<Return>", lambda e: self._on_barcode_entered())

        ctk.CTkButton(
            input_frame,
            text="Scan",
            width=80,
            command=self._on_barcode_entered,
        ).pack(side="left", padx=5)

        # Result frame
        self.result_frame = ctk.CTkFrame(self)
        self.result_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Status label
        self.status_label = ctk.CTkLabel(
            self.result_frame,
            text="Ready to scan",
            font=("Arial", 11),
            text_color="gray",
        )
        self.status_label.pack(pady=10)

        # Result display frame
        self.item_display_frame = ctk.CTkFrame(self.result_frame)
        self.item_display_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def _on_barcode_entered(self):
        """Handle manual barcode entry"""
        barcode = self.barcode_entry.get().strip()
        if barcode:
            self.barcode_scanner.process_barcode(barcode)
            self.barcode_entry.delete(0, "end")

    def _on_barcode_scanned(self, barcode: str):
        """Handle barcode or QR scan (callback from scanner)"""
        try:
            # Clear previous result
            for widget in self.item_display_frame.winfo_children():
                widget.destroy()

            result = self.scan_recognition_service.recognize(barcode)
            item = result.get("item")
            batch = result.get("batch")

            if result.get("found") and result.get("entity_type") == "batch" and batch and item:
                self.last_found_item = item
                self._display_batch_found(batch, item, result.get("matched_by"))
                if self.on_item_found:
                    self.on_item_found(item)
            elif result.get("found") and result.get("entity_type") == "item" and item:
                self.last_found_item = item
                self._display_item_found(item, result.get("matched_by"))

                if self.on_item_found:
                    self.on_item_found(item)
            else:
                self._display_item_not_found(barcode)

        except Exception as e:
            logger.error(f"Error scanning barcode: {e}")
            self._display_error(str(e))

    def _display_item_found(self, item, matched_by: Optional[str] = None):
        """Display found item information"""
        self.status_label.configure(
            text="✓ Item found!", text_color="green"
        )

        # Create item details frame
        details_frame = ctk.CTkFrame(self.item_display_frame)
        details_frame.pack(fill="both", expand=True, pady=10)

        # Item details
        details = [
            ("Item Name", item.item_name),
            ("Barcode", item.barcode),
            ("QR Code", item.qr_code or "-"),
            ("Category", item.category or "-"),
            ("Manufacturer", item.manufacturer or "-"),
            ("Current Quantity", str(item.current_quantity)),
            ("Minimum Quantity", str(item.minimum_quantity)),
            ("Maximum Quantity", str(item.maximum_quantity)),
            ("Expiry Date", item.expiry_date.strftime("%d-%m-%Y") if item.expiry_date else "-"),
            ("Stock Status", item.stock_status),
        ]
        if matched_by:
            details.insert(0, ("Matched By", matched_by.replace("_", " ").title()))

        for label, value in details:
            row_frame = ctk.CTkFrame(details_frame)
            row_frame.pack(fill="x", pady=5)

            ctk.CTkLabel(
                row_frame,
                text=f"{label}:",
                font=("Arial", 10, "bold"),
                width=140,
            ).pack(side="left", padx=5)

            ctk.CTkLabel(
                row_frame,
                text=str(value),
                font=("Arial", 10),
                text_color="lightblue" if label == "Stock Status" else "white",
            ).pack(side="left", padx=5)

        # Action buttons
        button_frame = ctk.CTkFrame(details_frame)
        button_frame.pack(fill="x", pady=20)

        ctk.CTkButton(
            button_frame,
            text="Record Usage",
            width=120,
            command=lambda: self._record_usage(item),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Edit Item",
            width=120,
            command=lambda: self._edit_item(item),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="View History",
            width=120,
            fg_color="gray",
            command=lambda: self._view_history(item),
        ).pack(side="left", padx=5)

    def _display_batch_found(self, batch, item, matched_by: Optional[str] = None):
        """Display found batch information together with its parent item."""
        self.status_label.configure(text="✓ Stock batch found!", text_color="green")

        details_frame = ctk.CTkFrame(self.item_display_frame)
        details_frame.pack(fill="both", expand=True, pady=10)

        details = [
        ("Batch ID", batch.batch_id),
        ("Product ID", batch.product_id),
        ("Item Name", item.item_name),
        ("Batch Number", batch.batch_number),
        ("Batch QR Code", batch.qr_code or "-"),
        ("Quantity Available", batch.quantity_available),
        ("Status", batch.status),
        ("Storage Location", batch.storage_location or "-"),
        ("Opened Date", batch.opened_date.strftime("%d-%m-%Y") if batch.opened_date else "-"),
        ("Expiry Date", batch.expiry_date.strftime("%d-%m-%Y") if batch.expiry_date else "-"),
        ("Product Barcode", item.barcode or "-"),
        ]
        if matched_by:
        details.insert(0, ("Matched By", matched_by.replace("_", " ").title()))

        for label, value in details:
        row_frame = ctk.CTkFrame(details_frame)
        row_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            row_frame,
            text=f"{label}:",
            font=("Arial", 10, "bold"),
            width=160,
        ).pack(side="left", padx=5)

        ctk.CTkLabel(row_frame, text=str(value), font=("Arial", 10)).pack(side="left", padx=5)

        button_frame = ctk.CTkFrame(details_frame)
        button_frame.pack(fill="x", pady=20)

        ctk.CTkButton(
        button_frame,
        text="Record Usage",
        width=120,
        command=lambda: self._record_usage(item),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
        button_frame,
        text="Edit Item",
        width=120,
        command=lambda: self._edit_item(item),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
        button_frame,
        text="View History",
        width=120,
        fg_color="gray",
        command=lambda: self._view_history(item),
        ).pack(side="left", padx=5)

    def _display_item_not_found(self, barcode: str):
        """Display item not found message"""
        self.status_label.configure(
        text=f"✗ No product or batch found: {barcode}", text_color="red"
        )

        message = ctk.CTkLabel(
            self.item_display_frame,
            text="No product or batch matched this barcode / QR code.\n\nOptions:\n• Check the code is correct\n• Add this product to inventory\n• Register a QR code against the item or batch",
            font=("Arial", 11),
            text_color="gray",
        )
        message.pack(pady=20)

        # Option to create new item
        ctk.CTkButton(
            self.item_display_frame,
            text="Add New Item with This Code",
            command=lambda: self._add_item_with_barcode(barcode),
        ).pack(pady=10)

    def _display_error(self, error: str):
        """Display error message"""
        self.status_label.configure(
            text="✗ Error", text_color="red"
        )

        error_label = ctk.CTkLabel(
            self.item_display_frame,
            text=f"Error: {error}",
            font=("Arial", 11),
            text_color="red",
        )
        error_label.pack(pady=20)

    def _record_usage(self, item):
        """Record item usage (stock movement)"""
        logger.info(f"Recording usage for item: {item.item_name}")
        # TODO: Implement stock movement dialog

    def _edit_item(self, item):
        """Edit item details"""
        logger.info(f"Editing item: {item.item_name}")
        # TODO: Open item detail form

    def _view_history(self, item):
        """View item stock movement history"""
        logger.info(f"Viewing history for item: {item.item_name}")
        # TODO: Show stock movements for this item

    def _add_item_with_barcode(self, barcode: str):
        """Open item creation form with scanned code pre-filled"""
        logger.info(f"Creating new item with scanned code: {barcode}")
        # TODO: Open item detail form with barcode pre-filled


class QuickScanDialog(ctk.CTkToplevel):
    """Quick barcode scan dialog with number pad and visual feedback"""

    def __init__(self, parent, on_barcode_scanned: Optional[Callable] = None):
        super().__init__(parent)
        self.title("Quick Barcode Scan")
        self.geometry("400x300")
        self.resizable(False, False)
        self.grab_set()

        self.on_barcode_scanned = on_barcode_scanned
        self.barcode_buffer = ""

        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog UI"""
        # Display frame
        display_frame = ctk.CTkFrame(self)
        display_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(display_frame, text="Scan barcode:", font=("Arial", 11, "bold")).pack(
            anchor="w"
        )

        self.barcode_display = ctk.CTkEntry(
            display_frame,
            font=("Arial", 16),
            justify="center",
            state="readonly",
        )
        self.barcode_display.pack(fill="x", pady=10)

        # Button frame
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            button_frame,
            text="Clear",
            width=100,
            fg_color="gray",
            command=self._clear,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Submit",
            width=100,
            command=self._submit,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=100,
            fg_color="red",
            command=self.destroy,
        ).pack(side="left", padx=5)

        # Focus on the window for keyboard input
        self.focus()
        self.bind("<KeyPress>", self._on_key_press)

    def _on_key_press(self, event):
        """Handle key press events"""
        if event.keysym == "Return":
            self._submit()
        elif event.keysym == "BackSpace":
            self.barcode_buffer = self.barcode_buffer[:-1]
        elif len(event.char) == 1 and event.char.isprintable():
            self.barcode_buffer += event.char

        self.barcode_display.configure(state="normal")
        self.barcode_display.delete(0, "end")
        self.barcode_display.insert(0, self.barcode_buffer)
        self.barcode_display.configure(state="readonly")

    def _clear(self):
        """Clear the buffer"""
        self.barcode_buffer = ""
        self.barcode_display.configure(state="normal")
        self.barcode_display.delete(0, "end")
        self.barcode_display.configure(state="readonly")

    def _submit(self):
        """Submit the barcode"""
        if self.barcode_buffer and self.on_barcode_scanned:
            self.on_barcode_scanned(self.barcode_buffer)
        self.destroy()
