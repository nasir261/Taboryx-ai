"""
Site dialog.
Dialog for creating and editing sites.
"""

import customtkinter as ctk
import logging
from typing import Optional

from src.models.models import Site
from src.ui.voice_typing_mixin import VoiceTypingMixin

logger = logging.getLogger(__name__)


class SiteDialog(VoiceTypingMixin, ctk.CTkToplevel):
    """Dialog for creating or editing a site."""

    def __init__(
        self,
        parent,
        site: Optional[Site] = None,
        on_save: Optional[callable] = None,
        on_delete: Optional[callable] = None,
    ):
        super().__init__(parent)
        self.title("Add Site" if not site else "Edit Site")
        self.geometry("500x420")
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)

        self.site = site
        self.on_save = on_save
        self.on_delete = on_delete
        self.fields = {}
        self.active_var = ctk.BooleanVar(value=True if site is None else bool(site.is_active))
        self._initialize_voice_typing()

        self._setup_ui()
        if site:
            self._load_site(site)

    def _setup_ui(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        title_text = "Create a new site" if not self.site else f"Edit site: {self.site.site_name}"
        ctk.CTkLabel(frame, text=title_text, font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 12))

        self.fields["site_name"] = self._create_field(frame, "Site Name *")
        self.fields["site_code"] = self._create_field(frame, "Site Code *")

        status_frame = ctk.CTkFrame(frame)
        status_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(status_frame, text="Active Status", font=("Arial", 11, "bold")).pack(anchor="w")
        ctk.CTkCheckBox(status_frame, text="Site is active", variable=self.active_var).pack(anchor="w", pady=5)

        self.status_label = ctk.CTkLabel(frame, text="", font=("Arial", 10), text_color="red")
        self.status_label.pack(anchor="w", pady=(8, 6))

        button_frame = ctk.CTkFrame(frame)
        button_frame.pack(fill="x", pady=(8, 0))

        ctk.CTkButton(button_frame, text="Save Site", width=130, command=self._save_site).pack(side="left", padx=5)
        if self.site and self.site.id:
            ctk.CTkButton(
                button_frame,
                text="Delete Site",
                width=130,
                fg_color="red",
                command=self._delete_site,
            ).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", width=130, fg_color="gray", command=self._close).pack(side="left", padx=5)

    def _create_field(self, parent, label: str):
        return self._create_voice_field(parent, label, multiline=False, width=360)

    def _load_site(self, site: Site):
        self.fields["site_name"].insert(0, site.site_name)
        self.fields["site_code"].insert(0, site.site_code)
        self.active_var.set(bool(site.is_active))

    def _save_site(self):
        site_name = self.fields["site_name"].get().strip()
        site_code = self.fields["site_code"].get().strip().upper()
        if not site_name:
            self._set_status("Site name is required", success=False)
            return
        if not site_code:
            self._set_status("Site code is required", success=False)
            return

        site = self.site or Site()
        site.site_name = site_name
        site.site_code = site_code
        site.is_active = bool(self.active_var.get())

        if self.on_save:
            self.on_save(site)
        self._close()

    def _delete_site(self):
        if not self.site or not self.site.id:
            self._set_status("Site cannot be deleted before it is created.", success=False)
            return
        if self.on_delete:
            self.on_delete(self.site)
        self._close()

    def _close(self):
        self.destroy()

    def _set_status(self, message: str, success: bool = True):
        self.status_label.configure(text=message, text_color="green" if success else "red")
        logger.info(message)
