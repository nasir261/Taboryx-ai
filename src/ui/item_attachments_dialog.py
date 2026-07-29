"""
Item Attachments Dialog
Attach and manage files linked to an inventory item.
"""

import os
import customtkinter as ctk
from tkinter import filedialog

from src.models.models import Item
from src.services.inventory_service import InventoryService


class ItemAttachmentsDialog(ctk.CTkToplevel):
    """Dialog for adding/removing item attachments."""

    def __init__(self, parent, item: Item):
        super().__init__(parent)
        self.item = item
        self.inventory_service = InventoryService()
        self.title(f"Attachments - {item.item_name}")
        self.geometry("900x560")
        self.resizable(True, True)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.attachments = []
        self._setup_ui()
        self._load_attachments()

    def _setup_ui(self):
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text=f"Item Attachments: {self.item.item_name}", font=("Arial", 14, "bold")).pack(
            side="left", padx=4
        )
        ctk.CTkButton(top, text="Add Attachment", width=140, command=self._add_attachment).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Refresh", width=100, fg_color="gray", command=self._load_attachments).pack(
            side="right", padx=4
        )

        self.status_label = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color="gray")
        self.status_label.pack(anchor="w", padx=14, pady=(0, 6))

        self.list_frame = ctk.CTkScrollableFrame(self, width=860, height=420)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self._render_header()

    def _render_header(self):
        header = ctk.CTkFrame(self.list_frame, fg_color="gray20", height=34)
        header.pack(fill="x", padx=5, pady=4)
        header.pack_propagate(False)
        columns = [("File", 300), ("Type", 80), ("Added", 150), ("Path", 240), ("Actions", 140)]
        for label, width in columns:
            ctk.CTkLabel(header, text=label, width=width, font=("Arial", 10, "bold")).pack(side="left", padx=3)

    def _load_attachments(self):
        for widget in self.list_frame.winfo_children()[1:]:
            widget.destroy()

        self.attachments = self.inventory_service.get_item_attachments(self.item.id)
        if not self.attachments:
            ctk.CTkLabel(self.list_frame, text="No attachments linked to this item.", text_color="gray").pack(pady=24)
            return

        for index, row in enumerate(self.attachments):
            self._add_attachment_row(row, index % 2 == 0)

    def _add_attachment_row(self, row: dict, alternate: bool):
        bg_color = "gray15" if alternate else "gray10"
        line = ctk.CTkFrame(self.list_frame, fg_color=bg_color, height=34)
        line.pack(fill="x", padx=5, pady=2)
        line.pack_propagate(False)

        values = [
            ((row.get("title") or row.get("file_name") or "")[:42], 300),
            ((row.get("file_type") or "file")[:12], 80),
            (self._fmt_datetime(row.get("uploaded_at")), 150),
            ((row.get("file_path") or "")[:38], 240),
        ]
        for text, width in values:
            ctk.CTkLabel(line, text=text, width=width).pack(side="left", padx=3)

        actions = ctk.CTkFrame(line, fg_color="transparent")
        actions.pack(side="left", padx=3)
        ctk.CTkButton(actions, text="Open", width=60, command=lambda p=row.get("file_path"): self._open_file(p)).pack(
            side="left", padx=2
        )
        ctk.CTkButton(
            actions,
            text="Delete",
            width=70,
            fg_color="red",
            command=lambda attachment_id=row.get("id"): self._delete_attachment(attachment_id),
        ).pack(side="left", padx=2)

    def _add_attachment(self):
        selected_file = filedialog.askopenfilename(
            title="Select attachment",
            filetypes=[
                ("Supported files", "*.pdf *.png *.jpg *.jpeg *.bmp *.txt *.doc *.docx *.xls *.xlsx"),
                ("All files", "*.*"),
            ],
        )
        if not selected_file:
            self.status_label.configure(text="Attachment selection cancelled.", text_color="gray")
            return

        success, message, _ = self.inventory_service.add_item_attachment(self.item.id, selected_file)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_attachments()

    def _delete_attachment(self, attachment_id: int):
        success, message = self.inventory_service.delete_item_attachment(attachment_id)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_attachments()

    def _open_file(self, file_path: str):
        if not file_path:
            self.status_label.configure(text="Attachment path missing.", text_color="red")
            return
        if not os.path.exists(file_path):
            self.status_label.configure(text="Attachment file no longer exists.", text_color="red")
            return
        os.startfile(file_path)

    @staticmethod
    def _fmt_datetime(value):
        if not value:
            return "-"
        text = str(value)
        if len(text) >= 19 and text[4] == "-" and text[7] == "-":
            return f"{text[8:10]}-{text[5:7]}-{text[0:4]} {text[11:16]}"
        return text
