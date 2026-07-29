"""
Item Detail/Form View
Dialog for adding and editing inventory items
"""

import customtkinter as ctk
from typing import Optional, Callable
from datetime import datetime
import logging
from src.models.models import Item
from src.services.inventory_service import InventoryService
from src.services.room_service import ClinicalRoomService
from src.services.supplier_service import SupplierService
from src.ui.item_attachments_dialog import ItemAttachmentsDialog
from src.ui.voice_typing_mixin import VoiceTypingMixin
from src.config import ITEM_CATEGORIES, CLINICAL_SAFETY_CHECK_NOTICE

logger = logging.getLogger(__name__)


class ItemDetailWindow(VoiceTypingMixin, ctk.CTkToplevel):
    """Dialog window for adding/editing inventory items"""
 
    def __init__(self, parent, item: Optional[Item] = None, on_save: Optional[Callable] = None,
                 initial_name: Optional[str] = None, initial_barcode: Optional[str] = None):
        super().__init__(parent)
        self.title("Add Item" if not item else "Edit Item")
        self.geometry("700x760")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.grab_set()
 
        self.item = item
        self.on_save = on_save
        self.initial_name = initial_name
        self.initial_barcode = initial_barcode
        self.inventory_service = InventoryService()
        self.room_service = ClinicalRoomService()
        self.supplier_service = SupplierService()
        self.form_data = {}
        self._initialize_voice_typing()
 
        self._setup_ui()
        if item:
            self._load_item_data()
        else:
            self._prefill_initial_data()

    def _setup_ui(self):
        """Setup the form UI"""
        # Main scrollable frame
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title = "Add New Item" if not self.item else f"Edit Item: {self.item.name}"
        ctk.CTkLabel(
            main_frame, text=title, font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(0, 20))

        product_id_text = f"Product ID: {self.item.id}" if self.item and self.item.id else "Product ID: assigned after save"
        ctk.CTkLabel(main_frame, text=product_id_text, font=("Arial", 11), text_color="gray").pack(anchor="w", pady=(0, 10))

        # Create form fields
        self.fields = {}

        self.fields["name"] = self._create_field(
            main_frame, "Item Name *", required=True
        )
        self.fields["product_code"] = self._create_field(main_frame, "Product Code")
        self.fields["generic_name"] = self._create_field(main_frame, "Generic Name")
        self.fields["brand"] = self._create_field(main_frame, "Brand")
        self.fields["barcode"] = self._create_field(main_frame, "Barcode *", required=True)
        self.fields["qr_code"] = self._create_field(main_frame, "QR Code")

        # Category dropdown
        category_frame = ctk.CTkFrame(main_frame)
        category_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(category_frame, text="Category:", font=("Arial", 11, "bold")).pack(
            anchor="w"
        )
        self.fields["category"] = ctk.CTkComboBox(
            category_frame, values=ITEM_CATEGORIES, state="readonly"
        )
        self.fields["category"].pack(fill="x", pady=5)

        self.fields["manufacturer"] = self._create_field(main_frame, "Manufacturer")
        self.supplier_map = {supplier.supplier_name: supplier.id for supplier in self.supplier_service.get_all_suppliers()}
        supplier_frame = ctk.CTkFrame(main_frame)
        supplier_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(supplier_frame, text="Supplier", font=("Arial", 11, "bold")).pack(anchor="w")
        self.fields["supplier"] = ctk.CTkComboBox(
            supplier_frame,
            values=list(self.supplier_map.keys()),
            state="normal",
        )
        self.fields["supplier"].pack(fill="x", pady=5)
        self.fields["supplier_product_code"] = self._create_field(main_frame, "Supplier Product Code")
        self.fields["unit_of_measurement"] = self._create_field(main_frame, "Unit of Measurement")

        self.fields["batch_number"] = self._create_field(main_frame, "Batch Number")

        # Dates
        self.fields["expiry_date"] = self._create_field(
            main_frame, "Expiry Date (DD-MM-YYYY)"
        )
        self.fields["date_received"] = self._create_field(
            main_frame, "Date Received (DD-MM-YYYY)"
        )

        # Pricing
        self.fields["purchase_price"] = self._create_field(
            main_frame, "Purchase Price (£)"
        )

        # Quantities
        qty_frame = ctk.CTkFrame(main_frame)
        qty_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(qty_frame, text="Quantities:", font=("Arial", 11, "bold")).pack(
            anchor="w"
        )

        qty_sub_frame = ctk.CTkFrame(qty_frame)
        qty_sub_frame.pack(fill="x")

        self.fields["current_quantity"] = self._create_inline_field(qty_sub_frame, "Current")
        self.fields["minimum_quantity"] = self._create_inline_field(qty_sub_frame, "Minimum Stock")
        self.fields["maximum_quantity"] = self._create_inline_field(qty_sub_frame, "Target Stock")
        self.fields["safety_stock_quantity"] = self._create_inline_field(qty_sub_frame, "Safety Stock")

        self.fields["lead_time_days"] = self._create_field(main_frame, "Lead Time in Days")

        # Storage location
        self.fields["storage_location"] = self._create_field(main_frame, "Storage Location")

        # Clinical room assignment
        room_names = [room.room_name for room in self.room_service.get_all_rooms()]
        room_frame = ctk.CTkFrame(main_frame)
        room_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(room_frame, text="Clinical Room:", font=("Arial", 11, "bold")).pack(anchor="w")
        self.fields["clinical_room"] = ctk.CTkComboBox(
            room_frame,
            values=room_names,
            state="normal",
        )
        self.fields["clinical_room"].pack(fill="x", pady=5)

        # Temperature requirements
        temp_frame = ctk.CTkFrame(main_frame)
        temp_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(temp_frame, text="Temperature Requirements:", font=("Arial", 11, "bold")).pack(
            anchor="w"
        )
        self.fields["temperature_requirements"] = self._create_field(temp_frame, "(e.g., 2-8°C)")

        # Checkboxes
        checkbox_frame = ctk.CTkFrame(main_frame)
        checkbox_frame.pack(fill="x", pady=10)

        self.fields["controlled_drug"] = ctk.CTkCheckBox(
            checkbox_frame, text="Controlled Drug"
        )
        self.fields["controlled_drug"].pack(anchor="w", pady=3)

        self.fields["requires_fridge"] = ctk.CTkCheckBox(
            checkbox_frame, text="Requires Refrigeration"
        )
        self.fields["requires_fridge"].pack(anchor="w", pady=3)

        self.fields["is_active"] = ctk.CTkCheckBox(
            checkbox_frame, text="Active Item"
        )
        self.fields["is_active"].pack(anchor="w", pady=3)
        self.fields["is_active"].select()

        # Notes
        self.fields["notes"] = self._create_field(main_frame, "Notes", multiline=True)

        ctk.CTkLabel(
            main_frame,
            text=CLINICAL_SAFETY_CHECK_NOTICE,
            wraplength=640,
            justify="left",
            font=("Arial", 10),
            text_color="orange",
        ).pack(anchor="w", pady=(8, 6))
 
        # Action buttons and status label at the bottom outside the scrollable content
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 20))
 
        button_frame = ctk.CTkFrame(action_frame)
        button_frame.pack(side="left")
 
        ctk.CTkButton(
            button_frame, text="Save Item", command=self._save_item, width=150
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame, text="Attachments", command=self._manage_attachments, width=150
        ).pack(side="left", padx=5)
 
        ctk.CTkButton(
            button_frame, text="Cancel", fg_color="gray", command=self._on_close, width=150
        ).pack(side="left", padx=5)
 
        self.status_label = ctk.CTkLabel(action_frame, text="", font=("Arial", 11), text_color="red")
        self.status_label.pack(side="left", padx=20)

    def _create_field(self, parent, label: str, required: bool = False, multiline: bool = False):
        """Create a labeled text field"""
        return self._create_voice_field(parent, label, multiline=multiline, required=required, width=400)

    def _create_inline_field(self, parent, label: str):
        """Create an inline labeled field for multiple columns"""
        return self._create_inline_voice_field(parent, label, width=100)
 
    def _prefill_initial_data(self):
        """Prefill a new item form with initial values"""
        if self.initial_name:
            self.fields["name"].insert(0, self.initial_name)
        if self.initial_barcode:
            self.fields["barcode"].insert(0, self.initial_barcode)
 
    def _load_item_data(self):
        """Load existing item data into form"""
        if not self.item:
            return

        self.fields["name"].insert(0, self.item.name)
        self.fields["product_code"].insert(0, self.item.product_code or "")
        self.fields["generic_name"].insert(0, self.item.generic_name or "")
        self.fields["brand"].insert(0, self.item.brand or "")
        self.fields["barcode"].insert(0, self.item.barcode or "")
        self.fields["qr_code"].insert(0, self.item.qr_code or "")
        self.fields["category"].set(self.item.category or "")
        self.fields["manufacturer"].insert(0, self.item.manufacturer or "")
        if self.item.supplier_id:
            supplier = self.supplier_service.get_supplier_by_id(self.item.supplier_id)
            if supplier:
                self.fields["supplier"].set(supplier.supplier_name)
        self.fields["supplier_product_code"].insert(0, self.item.supplier_product_code or "")
        self.fields["unit_of_measurement"].insert(0, self.item.unit_of_measurement or "")
        self.fields["batch_number"].insert(0, self.item.batch_number or "")

        if self.item.expiry_date:
            self.fields["expiry_date"].insert(0, self.item.expiry_date.strftime("%d-%m-%Y"))
        if self.item.date_received:
            self.fields["date_received"].insert(0, self.item.date_received.strftime("%d-%m-%Y"))

        if self.item.purchase_price:
            self.fields["purchase_price"].insert(0, str(self.item.purchase_price))

        self.fields["current_quantity"].insert(0, str(self.item.current_quantity))
        self.fields["minimum_quantity"].insert(0, str(self.item.minimum_quantity))
        self.fields["maximum_quantity"].insert(0, str(self.item.maximum_quantity))
        self.fields["safety_stock_quantity"].insert(0, str(self.item.safety_stock_quantity or 0))
        if self.item.lead_time_days is not None:
            self.fields["lead_time_days"].insert(0, str(self.item.lead_time_days))

        self.fields["storage_location"].insert(0, self.item.storage_location or "")
        if self.fields["clinical_room"] and self.item.clinical_room:
            self.fields["clinical_room"].set(self.item.clinical_room)
        self.fields["temperature_requirements"].insert(0, self.item.temperature_requirements or "")

        if self.item.controlled_drug:
            self.fields["controlled_drug"].select()
        if self.item.requires_fridge:
            self.fields["requires_fridge"].select()
        if not self.item.is_active:
            self.fields["is_active"].deselect()

        if self.fields["notes"]:
            self.fields["notes"].insert("1.0", self.item.notes or "")

    def _save_item(self):
        """Validate and save item"""
        try:
            # Validate required fields
            name = self.fields["name"].get().strip()
            if not name:
                self._show_error("Item name is required")
                return
 
            barcode = self.fields["barcode"].get().strip()
            if not barcode:
                self._show_error("Barcode is required")
                return
 
            # Parse quantities
            try:
                current_qty = int(self.fields["current_quantity"].get() or 0)
                min_qty = int(self.fields["minimum_quantity"].get() or 0)
                max_qty = int(self.fields["maximum_quantity"].get() or 0)
                safety_stock_qty = int(self.fields["safety_stock_quantity"].get() or 0)
            except ValueError:
                self._show_error("Quantities must be numbers")
                return

            lead_time_days = None
            if self.fields["lead_time_days"].get().strip():
                try:
                    lead_time_days = int(self.fields["lead_time_days"].get().strip())
                except ValueError:
                    self._show_error("Lead time in days must be a whole number")
                    return

            # Parse optional fields
            expiry_date = None
            if self.fields["expiry_date"].get().strip():
                try:
                    expiry_date = self._parse_date_input(self.fields["expiry_date"].get())
                except ValueError:
                    self._show_error("Invalid expiry date format (use DD-MM-YYYY)")
                    return

            date_received = None
            if self.fields["date_received"].get().strip():
                try:
                    date_received = self._parse_date_input(self.fields["date_received"].get())
                except ValueError:
                    self._show_error("Invalid date received format (use DD-MM-YYYY)")
                    return

            purchase_price = None
            if self.fields["purchase_price"].get().strip():
                try:
                    purchase_price = float(self.fields["purchase_price"].get())
                except ValueError:
                    self._show_error("Invalid purchase price (must be a number)")
                    return

            # Get notes
            notes_field = self.fields["notes"]
            if isinstance(notes_field, ctk.CTkTextbox):
                notes = notes_field.get("1.0", "end").strip()
            else:
                notes = ""

            # Create or update item
            if self.item:
                # Update existing
                self.item.name = name
                self.item.product_code = self.fields["product_code"].get().strip() or None
                self.item.generic_name = self.fields["generic_name"].get().strip() or None
                self.item.brand = self.fields["brand"].get().strip() or None
                self.item.barcode = barcode
                self.item.qr_code = self.fields["qr_code"].get().strip() or None
                self.item.category = self.fields["category"].get() or None
                self.item.manufacturer = self.fields["manufacturer"].get().strip() or None
                supplier_name = self.fields["supplier"].get().strip()
                supplier = self.supplier_service.get_supplier_by_name(supplier_name) if supplier_name else None
                if supplier_name and not supplier:
                    self._show_error("Supplier not found. Please select from the supplier list.")
                    return
                self.item.supplier_id = supplier.id if supplier else None
                self.item.supplier_product_code = self.fields["supplier_product_code"].get().strip() or None
                self.item.batch_number = self.fields["batch_number"].get().strip() or None
                self.item.expiry_date = expiry_date
                self.item.date_received = date_received
                self.item.purchase_price = purchase_price
                self.item.unit_of_measurement = self.fields["unit_of_measurement"].get().strip() or None
                self.item.current_quantity = current_qty
                self.item.minimum_quantity = min_qty
                self.item.maximum_quantity = max_qty
                self.item.lead_time_days = lead_time_days
                self.item.safety_stock_quantity = safety_stock_qty
                self.item.storage_location = self.fields["storage_location"].get().strip() or None
                self.item.clinical_room = self.fields["clinical_room"].get().strip() or None
                self.item.temperature_requirements = self.fields["temperature_requirements"].get().strip() or None
                self.item.controlled_drug = self.fields["controlled_drug"].get()
                self.item.requires_fridge = self.fields["requires_fridge"].get()
                self.item.is_active = self.fields["is_active"].get()
                self.item.notes = notes

                success, message = self.inventory_service.update_item(self.item)
                if not success:
                    self._show_error(message)
                    return
                logger.info(f"Item updated: {self.item.id}")
            else:
                # Create new
                supplier_name = self.fields["supplier"].get().strip()
                supplier = self.supplier_service.get_supplier_by_name(supplier_name) if supplier_name else None
                if supplier_name and not supplier:
                    self._show_error("Supplier not found. Please select from the supplier list.")
                    return
                supplier_id = supplier.id if supplier else None
 
                success, message, _item_id = self.inventory_service.add_item(
                    name=name,
                    product_code=self.fields["product_code"].get().strip() or None,
                    generic_name=self.fields["generic_name"].get().strip() or None,
                    brand=self.fields["brand"].get().strip() or None,
                    barcode=barcode,
                    qr_code=self.fields["qr_code"].get().strip() or None,
                    category=self.fields["category"].get() or None,
                    manufacturer=self.fields["manufacturer"].get().strip() or None,
                    supplier_id=supplier_id,
                    supplier_product_code=self.fields["supplier_product_code"].get().strip() or None,
                    batch_number=self.fields["batch_number"].get().strip() or None,
                    expiry_date=expiry_date,
                    date_received=date_received,
                    purchase_price=purchase_price,
                    unit_of_measurement=self.fields["unit_of_measurement"].get().strip() or None,
                    current_quantity=current_qty,
                    minimum_quantity=min_qty,
                    maximum_quantity=max_qty,
                    lead_time_days=lead_time_days,
                    safety_stock_quantity=safety_stock_qty,
                    storage_location=self.fields["storage_location"].get().strip() or None,
                    clinical_room=self.fields["clinical_room"].get().strip() or None,
                    temperature_requirements=self.fields["temperature_requirements"].get().strip() or None,
                    controlled_drug=self.fields["controlled_drug"].get(),
                    requires_fridge=self.fields["requires_fridge"].get(),
                    is_active=self.fields["is_active"].get(),
                    notes=notes,
                )
                if not success:
                    self._show_error(message)
                    return
                logger.info(f"Item created: {name}")

            if self.on_save:
                self.on_save()

            self.destroy()

        except Exception as e:
            logger.error(f"Error saving item: {e}")
            self._show_error(f"Error saving item: {str(e)}")

    def _show_error(self, message: str):
        """Show error message"""
        logger.error(message)
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.configure(text=message, text_color="red")
        else:
            print(f"ERROR: {message}")
 
    def _on_close(self):
        """Handle window close action"""
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _manage_attachments(self):
        if not self.item or not self.item.id:
            self._show_error("Save the item first before adding attachments.")
            return
        ItemAttachmentsDialog(self, self.item)

    @staticmethod
    def _parse_date_input(value: str):
        """Parse user-entered date with dd-mm-yyyy as default format."""
        value = value.strip()
        for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        raise ValueError("Invalid date format")
