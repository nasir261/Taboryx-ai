"""
Supplier Dialog
Dialog for creating and editing suppliers.
"""

import customtkinter as ctk
import logging
from typing import Optional
from src.models.models import Supplier
from src.ui.voice_typing_mixin import VoiceTypingMixin

logger = logging.getLogger(__name__)


class SupplierDialog(VoiceTypingMixin, ctk.CTkToplevel):
    """Dialog for creating or editing a supplier"""

    def __init__(self, parent, supplier: Optional[Supplier] = None, on_save: Optional[callable] = None):
        super().__init__(parent)
        self.title("Add Supplier" if not supplier else "Edit Supplier")
        self.geometry("560x580")
        self.resizable(False, False)
        self.grab_set()

        self.supplier = supplier
        self.on_save = on_save
        self.fields = {}
        self._initialize_voice_typing()

        self._setup_ui()
        if supplier:
            self._load_supplier(supplier)

    def _setup_ui(self):
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        title_text = "Create a new supplier" if not self.supplier else f"Edit supplier: {self.supplier.supplier_name}"
        ctk.CTkLabel(main_frame, text=title_text, font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 20))

        self.fields["supplier_name"] = self._create_field(main_frame, "Supplier Name *")
        self.fields["address"] = self._create_field(main_frame, "Address", multiline=True)
        self.fields["telephone"] = self._create_field(main_frame, "Telephone")
        self.fields["email"] = self._create_field(main_frame, "Email")
        self.fields["website"] = self._create_field(main_frame, "Website")
        self.fields["lead_time_days"] = self._create_field(main_frame, "Lead Time (days)")
        self.fields["contact_person"] = self._create_field(main_frame, "Contact Person")
        self.fields["notes"] = self._create_field(main_frame, "Notes", multiline=True)

        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=20)

        ctk.CTkButton(button_frame, text="Save Supplier", width=140, command=self._save_supplier).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", width=140, fg_color="gray", command=self.destroy).pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(main_frame, text="", font=("Arial", 11), text_color="red")
        self.status_label.pack(anchor="w", pady=5)

    def _create_field(self, parent, label: str, multiline: bool = False):
        return self._create_voice_field(parent, label, multiline=multiline, width=360)

    def _load_supplier(self, supplier: Supplier):
        self.fields["supplier_name"].insert(0, supplier.supplier_name)
        self.fields["address"].insert("1.0", supplier.address or "")
        self.fields["telephone"].insert(0, supplier.telephone or "")
        self.fields["email"].insert(0, supplier.email or "")
        self.fields["website"].insert(0, supplier.website or "")
        self.fields["lead_time_days"].insert(0, str(supplier.lead_time_days or ""))
        self.fields["contact_person"].insert(0, supplier.contact_person or "")
        self.fields["notes"].insert("1.0", supplier.notes or "")

    def _save_supplier(self):
        supplier_name = self.fields["supplier_name"].get().strip()
        if not supplier_name:
            self._set_status("Supplier name is required", success=False)
            return

        supplier_data = Supplier(
            supplier_name=supplier_name,
            address=self.fields["address"].get("1.0", "end").strip() or None,
            telephone=self.fields["telephone"].get().strip() or None,
            email=self.fields["email"].get().strip() or None,
            website=self.fields["website"].get().strip() or None,
            lead_time_days=int(self.fields["lead_time_days"].get().strip()) if self.fields["lead_time_days"].get().strip().isdigit() else None,
            contact_person=self.fields["contact_person"].get().strip() or None,
            notes=self.fields["notes"].get("1.0", "end").strip() or None,
        )

        if self.supplier:
            supplier_data.id = self.supplier.id

        if self.on_save:
            self.on_save(supplier_data)
        self.destroy()

    def _set_status(self, message: str, success: bool = True):
        self.status_label.configure(text=message, text_color="green" if success else "red")
        logger.info(message)
