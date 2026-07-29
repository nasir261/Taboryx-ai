"""
Sites View
UI for managing sites.
"""

import customtkinter as ctk
import logging

from src.models.models import Site
from src.services.site_service import SiteService
from src.ui.site_dialog import SiteDialog
from src.ui.list_style_helpers import make_badge

logger = logging.getLogger(__name__)


class SitesView(ctk.CTkFrame):
    """Frame for managing sites."""

    def __init__(self, parent):
        super().__init__(parent)
        self.site_service = SiteService()
        self.current_sites = []

        self._setup_ui()
        self._load_sites()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="Sites", font=("Segoe UI", 19, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(top_frame, text="Add Site", width=120, command=self._add_site).pack(side="right", padx=5)
        ctk.CTkButton(top_frame, text="Refresh", width=100, fg_color="gray", command=self._load_sites).pack(side="right", padx=5)

        self.status_label = ctk.CTkLabel(self, text="", font=("Arial", 12), text_color="gray")
        self.status_label.pack(anchor="w", padx=14, pady=(0, 8))

        self.sites_frame = ctk.CTkScrollableFrame(self, width=1100, height=520)
        self.sites_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._render_header()

    def _render_header(self):
        header = ctk.CTkFrame(self.sites_frame, fg_color="gray20", height=35)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)

        columns = [("Site ID", 90), ("Site Name", 300), ("Site Code", 160), ("Status", 110), ("Actions", 220)]
        for label, width in columns:
            ctk.CTkLabel(header, text=label, width=width, font=("Segoe UI", 12, "bold")).pack(side="left", padx=3)

    def _load_sites(self):
        for widget in self.sites_frame.winfo_children()[1:]:
            widget.destroy()

        self.current_sites = self.site_service.get_all_sites()
        if not self.current_sites:
            ctk.CTkLabel(self.sites_frame, text="No sites configured.", font=("Arial", 12), text_color="gray").pack(pady=30)
            self.status_label.configure(text="No sites configured.", text_color="gray")
            return

        self.status_label.configure(text=f"Showing {len(self.current_sites)} site(s).", text_color="gray")
        for index, site in enumerate(self.current_sites):
            self._add_site_row(site, index % 2 == 0)

    def _add_site_row(self, site: Site, alternate: bool):
        bg = "#111b2e" if alternate else "#0d1727"
        row = ctk.CTkFrame(self.sites_frame, fg_color=bg, height=35)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)

        values = [
            (str(site.site_id or ""), 90),
            (f"🏢 {site.site_name}", 300),
            (site.site_code, 160),
        ]
        for text, width in values:
            ctk.CTkLabel(row, text=text, width=width, font=("Segoe UI", 12)).pack(side="left", padx=3)

        status = "Active" if site.is_active else "Inactive"
        make_badge(
            row,
            f"● {status}",
            "#0f766e" if site.is_active else "#7c2d12",
            "#d1fae5" if site.is_active else "#fde68a",
            110,
        ).pack(side="left", padx=3)

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="left", padx=3)
        ctk.CTkButton(actions, text="✎", width=28, height=24, fg_color="#1d4ed8", command=lambda s=site: self._edit_site(s)).pack(side="left", padx=2)
        ctk.CTkButton(actions, text="🗑", width=28, height=24, fg_color="#b91c1c", command=lambda s=site: self._delete_site(s)).pack(side="left", padx=2)

    def _add_site(self):
        SiteDialog(self, on_save=self._on_site_created)

    def _edit_site(self, site: Site):
        SiteDialog(self, site=site, on_save=self._on_site_updated, on_delete=self._on_site_deleted)

    def _delete_site(self, site: Site):
        success, message = self.site_service.delete_site(site.id)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_sites()
        else:
            logger.error(message)

    def _on_site_created(self, site: Site):
        success, message, _ = self.site_service.create_site(site)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_sites()
        else:
            logger.error(message)

    def _on_site_updated(self, site: Site):
        success, message = self.site_service.update_site(site)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_sites()
        else:
            logger.error(message)

    def _on_site_deleted(self, site: Site):
        self._delete_site(site)
