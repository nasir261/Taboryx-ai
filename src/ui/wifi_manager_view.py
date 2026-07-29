"""Admin-only Wi-Fi connection management view."""

import ctypes
import customtkinter as ctk
import logging
import sys
from typing import Optional

from src.services.wifi_connection_service import WiFiConnectionService

logger = logging.getLogger(__name__)


def _is_windows_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _relaunch_as_admin():
    """Re-launch the current process with UAC elevation."""
    try:
        executable = sys.executable
        args = " ".join(f'"{a}"' for a in sys.argv)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, args, None, 1)
    except Exception as exc:
        logger.error("Failed to relaunch as admin: %s", exc)


class WiFiManagerView(ctk.CTkFrame):
    """A compact admin-only Wi-Fi connection screen."""

    def __init__(self, parent, user_role: str):
        super().__init__(parent, fg_color="transparent")
        self.user_role = (user_role or "").lower()
        self.service = WiFiConnectionService()
        self._create_widgets()
        self._refresh_networks()

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="#0f1d37", corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="Wi-Fi Connection Manager", font=("Segoe UI", 20, "bold"), text_color="#6ee7ff").grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(header, text="Admin-only network discovery and connection for local Wi-Fi access.", font=("Segoe UI", 13), text_color="#8fa2c9").grid(row=1, column=0, sticky="w", padx=14, pady=(0, 6))

        # Always show elevation status and relaunch button
        is_admin = _is_windows_admin()
        elev_color = "#14532d" if is_admin else "#7c2d12"
        elev_text = "Running as Administrator — Wi-Fi connection is enabled." if is_admin else "NOT running as Administrator.  Wi-Fi connect requires elevation."
        elev_text_color = "#86efac" if is_admin else "#fcd34d"

        elev_frame = ctk.CTkFrame(header, fg_color=elev_color, corner_radius=8)
        elev_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        elev_frame.grid_columnconfigure(0, weight=1)
        elev_frame.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            elev_frame,
            text=elev_text,
            text_color=elev_text_color,
            font=("Segoe UI", 12, "bold"),
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=10, pady=8)

        if not is_admin:
            ctk.CTkButton(
                elev_frame,
                text="Restart app as Administrator",
                fg_color="#dc2626",
                hover_color="#b91c1c",
                font=("Segoe UI", 12, "bold"),
                width=260,
                command=_relaunch_as_admin,
            ).grid(row=0, column=1, padx=(4, 10), pady=8)

        body = ctk.CTkFrame(self, fg_color="#0f1d37", corner_radius=12)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        top_controls = ctk.CTkFrame(body, fg_color="transparent")
        top_controls.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        top_controls.grid_columnconfigure(0, weight=1)
        top_controls.grid_columnconfigure(1, weight=0)
        self.refresh_button = ctk.CTkButton(top_controls, text="Refresh networks", command=self._refresh_networks)
        self.refresh_button.grid(row=0, column=0, sticky="w")
        self.status_label = ctk.CTkLabel(top_controls, text="", text_color="#fbbf24")
        self.status_label.grid(row=0, column=1, sticky="e", padx=(8, 0))

        self.network_box = ctk.CTkScrollableFrame(body, fg_color="#091426", corner_radius=10)
        self.network_box.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        self.network_box.grid_columnconfigure(0, weight=1)

        self.form_frame = ctk.CTkFrame(self.network_box, fg_color="transparent")
        self.form_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        self.form_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.form_frame, text="SSID", font=("Segoe UI", 12, "bold"), text_color="#dbeafe").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        self.ssid_var = ctk.StringVar(value="")
        self.ssid_entry = ctk.CTkEntry(self.form_frame, textvariable=self.ssid_var, placeholder_text="e.g. Hospital-Wifi")
        self.ssid_entry.grid(row=0, column=1, sticky="ew", pady=4)

        ctk.CTkLabel(self.form_frame, text="Username", font=("Segoe UI", 12, "bold"), text_color="#dbeafe").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        self.username_var = ctk.StringVar(value="")
        self.username_entry = ctk.CTkEntry(self.form_frame, textvariable=self.username_var, placeholder_text="Optional")
        self.username_entry.grid(row=1, column=1, sticky="ew", pady=4)

        ctk.CTkLabel(self.form_frame, text="Password", font=("Segoe UI", 12, "bold"), text_color="#dbeafe").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=4)
        self.password_var = ctk.StringVar(value="")
        self.password_entry = ctk.CTkEntry(self.form_frame, textvariable=self.password_var, show="*", placeholder_text="Wi-Fi password")
        self.password_entry.grid(row=2, column=1, sticky="ew", pady=4)

        self.connect_button = ctk.CTkButton(self.form_frame, text="Save and connect", command=self._connect_selected_network)
        self.connect_button.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 4))

        self.networks_frame = ctk.CTkFrame(self.network_box, fg_color="transparent")
        self.networks_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(10, 4))
        self.networks_frame.grid_columnconfigure(0, weight=1)

        if self.user_role != "administrator":
            ctk.CTkLabel(self.networks_frame, text="Only administrators can manage Wi-Fi connections.", text_color="#fca5a5").pack(anchor="w")
            self.connect_button.configure(state="disabled")
            self.refresh_button.configure(state="disabled")
            self.ssid_entry.configure(state="disabled")
            self.username_entry.configure(state="disabled")
            self.password_entry.configure(state="disabled")

    def _refresh_networks(self):
        if self.user_role != "administrator":
            self.status_label.configure(text="Access denied")
            return

        self.status_label.configure(text="Scanning... please wait (2 sec)", text_color="#fbbf24")
        self.refresh_button.configure(state="disabled")
        self.update_idletasks()

        try:
            networks = self.service.scan_available_networks()
        except Exception as exc:
            self.status_label.configure(text=str(exc), text_color="#fca5a5")
            self.refresh_button.configure(state="normal")
            return

        self.refresh_button.configure(state="normal")

        for widget in self.networks_frame.winfo_children():
            widget.destroy()

        if not networks:
            ctk.CTkLabel(self.networks_frame, text="No nearby Wi-Fi networks detected.", text_color="#8fa2c9").pack(anchor="w")
            self.status_label.configure(text="Scan complete — no networks found", text_color="#86efac")
            return

        for network in networks:
            ssid = network["ssid"]
            signal = network.get("signal", "")
            is_connected = network.get("connected", False)

            label = ssid
            if signal:
                label = f"{ssid}   [{signal}]"
            if is_connected:
                label = f"✓  {label}  (connected)"

            row_color = "#1a3a1a" if is_connected else "#111827"
            text_color = "#86efac" if is_connected else "#dbeafe"

            button = ctk.CTkButton(
                self.networks_frame,
                text=label,
                anchor="w",
                fg_color=row_color,
                hover_color="#1f2937",
                text_color=text_color,
                command=lambda s=ssid: self._populate_ssid(s),
            )
            button.pack(fill="x", pady=2)

        self.status_label.configure(text=f"Found {len(networks)} nearby networks", text_color="#86efac")

    def _populate_ssid(self, ssid: str):
        self.ssid_var.set(ssid)
        try:
            username, password = self.service.get_saved_network_credentials(ssid)
        except Exception:
            username = ""
            password = ""
        self.username_var.set(username)
        self.password_var.set(password)

    def _connect_selected_network(self):
        if self.user_role != "administrator":
            self.status_label.configure(text="Only administrators can manage Wi-Fi.", text_color="#fca5a5")
            return

        ssid = self.ssid_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        if not ssid or not password:
            self.status_label.configure(text="Please enter both SSID and password.", text_color="#fca5a5")
            return

        if not _is_windows_admin():
            self.status_label.configure(
                text="Please use the red 'Restart app as Administrator' button above first.",
                text_color="#fcd34d",
            )
            return

        try:
            success, message = self.service.connect_to_network(ssid, password, username=username)
        except Exception as exc:
            logger.error("Wi-Fi connect failed: %s", exc)
            self.status_label.configure(text=str(exc), text_color="#fca5a5")
            return

        if success:
            self.status_label.configure(text=message, text_color="#86efac")
        else:
            self.status_label.configure(text=message, text_color="#fca5a5")
