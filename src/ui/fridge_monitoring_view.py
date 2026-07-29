"""
Desktop fridge monitoring view for Wi-Fi enabled pharmacy fridges.
"""

import logging
from typing import Dict, List, Optional

import customtkinter as ctk

from src.services.fridge_monitoring_service import FridgeMonitoringService
from src.services.room_service import ClinicalRoomService
from src.ui.list_style_helpers import make_badge

logger = logging.getLogger(__name__)


class FridgeMonitoringView(ctk.CTkFrame):
    """Frame for managing fridge devices and temperature readings."""

    def __init__(self, parent):
        super().__init__(parent)
        self.fridge_service = FridgeMonitoringService()
        self.room_service = ClinicalRoomService()
        self.current_fridges: List[Dict] = []
        self.room_lookup: Dict[str, int] = {}
        self.fridge_lookup: Dict[str, int] = {}
        self._setup_ui()
        self._load_fridges()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1)
        self.grid_rowconfigure(4, weight=0)
        self.grid_rowconfigure(4, minsize=30)

        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top_frame, text="Fridge Monitoring", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            top_frame,
            text="Register connected pharmacy fridges and log live temperature readings.",
            text_color="#8fa2c9",
            font=("Segoe UI", 12),
        ).grid(row=1, column=0, sticky="w", pady=(2, 8))
        ctk.CTkButton(top_frame, text="Refresh", width=100, fg_color="gray", command=self._load_fridges).grid(
            row=0, column=1, rowspan=2, sticky="e"
        )

        forms_frame = ctk.CTkFrame(self, fg_color="transparent")
        forms_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        forms_frame.grid_columnconfigure(0, weight=1)
        forms_frame.grid_columnconfigure(1, weight=1)

        self.register_frame = ctk.CTkFrame(forms_frame, fg_color="#0f1d37", corner_radius=12)
        self.register_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.register_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.register_frame, text="Register Fridge", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=12, pady=(12, 8))

        fields = [
            ("Device Name", "device_name"),
            ("Device Code", "device_code"),
            ("Location", "location"),
            ("Endpoint URL", "endpoint_url"),
            ("Min Temperature", "min_temperature"),
            ("Max Temperature", "max_temperature"),
            ("Notes", "notes"),
        ]
        self.register_fields = {}
        for label_text, key in fields:
            row = ctk.CTkFrame(self.register_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(row, text=label_text, width=140, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row)
            entry.pack(side="left", fill="x", expand=True)
            self.register_fields[key] = entry

        self.room_var = ctk.StringVar(value="")
        room_row = ctk.CTkFrame(self.register_frame, fg_color="transparent")
        room_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(room_row, text="Room", width=140, anchor="w").pack(side="left")
        self.room_menu = ctk.CTkOptionMenu(room_row, variable=self.room_var, values=["No rooms configured"])
        self.room_menu.pack(side="left", fill="x", expand=True)

        self.connection_var = ctk.StringVar(value="wifi")
        connection_row = ctk.CTkFrame(self.register_frame, fg_color="transparent")
        connection_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(connection_row, text="Connection", width=140, anchor="w").pack(side="left")
        self.connection_menu = ctk.CTkOptionMenu(connection_row, variable=self.connection_var, values=["wifi", "network", "manual"])
        self.connection_menu.pack(side="left", fill="x", expand=True)

        self.active_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self.register_frame, text="Active", variable=self.active_var).pack(anchor="w", padx=12, pady=(6, 10))
        ctk.CTkButton(
            self.register_frame,
            text="Register Fridge",
            command=self._register_fridge,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
        ).pack(anchor="e", padx=12, pady=(0, 12))

        self.reading_frame = ctk.CTkFrame(forms_frame, fg_color="#0f1d37", corner_radius=12)
        self.reading_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.reading_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.reading_frame, text="Record Reading", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=12, pady=(12, 8))

        fridge_row = ctk.CTkFrame(self.reading_frame, fg_color="transparent")
        fridge_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(fridge_row, text="Fridge", width=140, anchor="w").pack(side="left")
        self.fridge_var = ctk.StringVar(value="")
        self.fridge_menu = ctk.CTkOptionMenu(fridge_row, variable=self.fridge_var, values=["No fridges registered"])
        self.fridge_menu.pack(side="left", fill="x", expand=True)

        temp_row = ctk.CTkFrame(self.reading_frame, fg_color="transparent")
        temp_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(temp_row, text="Temperature °C", width=140, anchor="w").pack(side="left")
        self.temperature_entry = ctk.CTkEntry(temp_row)
        self.temperature_entry.pack(side="left", fill="x", expand=True)

        source_row = ctk.CTkFrame(self.reading_frame, fg_color="transparent")
        source_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(source_row, text="Source", width=140, anchor="w").pack(side="left")
        self.source_var = ctk.StringVar(value="wifi")
        self.source_menu = ctk.CTkOptionMenu(source_row, variable=self.source_var, values=["wifi", "manual", "network"])
        self.source_menu.pack(side="left", fill="x", expand=True)

        notes_row = ctk.CTkFrame(self.reading_frame, fg_color="transparent")
        notes_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(notes_row, text="Notes", width=140, anchor="w").pack(side="left")
        self.reading_notes_entry = ctk.CTkEntry(notes_row)
        self.reading_notes_entry.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            self.reading_frame,
            text="Save Reading",
            command=self._record_reading,
            fg_color="#0f766e",
            hover_color="#0d9488",
        ).pack(anchor="e", padx=12, pady=(8, 12))

        wifi_actions = ctk.CTkFrame(self.reading_frame, fg_color="transparent")
        wifi_actions.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(
            wifi_actions,
            text="Test Wi-Fi Connection",
            command=self._test_wifi_connection,
            fg_color="#1d4ed8",
            hover_color="#1e40af",
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            wifi_actions,
            text="Sync from Wi-Fi Endpoint",
            command=self._sync_from_wifi_endpoint,
            fg_color="#334155",
            hover_color="#1f2937",
        ).pack(side="left")

        header = ctk.CTkFrame(self, fg_color="#111b2e", corner_radius=10)
        header.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))
        header.grid_columnconfigure(0, weight=2)
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=1)
        header.grid_columnconfigure(3, weight=1)
        header.grid_columnconfigure(4, weight=1)
        ctk.CTkLabel(header, text="Fridge", font=("Segoe UI", 12, "bold"), width=220).grid(row=0, column=0, padx=8, pady=8)
        ctk.CTkLabel(header, text="Location", font=("Segoe UI", 12, "bold"), width=140).grid(row=0, column=1, padx=8, pady=8)
        ctk.CTkLabel(header, text="Latest Temp", font=("Segoe UI", 12, "bold"), width=100).grid(row=0, column=2, padx=8, pady=8)
        ctk.CTkLabel(header, text="Status", font=("Segoe UI", 12, "bold"), width=100).grid(row=0, column=3, padx=8, pady=8)
        ctk.CTkLabel(header, text="Last Update", font=("Segoe UI", 12, "bold"), width=160).grid(row=0, column=4, padx=8, pady=8)

        self.fridges_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", height=220)
        self.fridges_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.fridges_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self,
            text="",
            text_color="#86efac",
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        )
        self.status_label.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 8))

    def _load_fridges(self):
        self._clear_fridge_rows()
        self.current_fridges = self.fridge_service.get_fridges()
        self._populate_room_dropdown()
        self._populate_fridge_dropdown()

        if not self.current_fridges:
            ctk.CTkLabel(self.fridges_frame, text="No fridges registered yet.", text_color="#8fa2c9").pack(pady=20)
            return

        for fridge in self.current_fridges:
            self._add_fridge_row(fridge)

    def _clear_fridge_rows(self):
        for widget in self.fridges_frame.winfo_children():
            widget.destroy()

    def _populate_room_dropdown(self):
        rooms = self.room_service.get_all_rooms()
        self.room_lookup = {room.room_name: room.id for room in rooms if room.room_name}
        values = [room.room_name for room in rooms if room.room_name]
        if not values:
            values = ["No rooms configured"]
        self.room_menu.configure(values=values)
        if values and values[0] != "No rooms configured":
            self.room_var.set(values[0])
        else:
            self.room_var.set("")

    def _populate_fridge_dropdown(self):
        self.fridge_lookup = {fridge.get("device_name", ""): fridge.get("id") for fridge in self.current_fridges if fridge.get("device_name")}
        values = [fridge.get("device_name") for fridge in self.current_fridges if fridge.get("device_name")]
        if not values:
            values = ["No fridges registered"]
        self.fridge_menu.configure(values=values)
        if values and values[0] != "No fridges registered":
            self.fridge_var.set(values[0])
        else:
            self.fridge_var.set("")

    def _add_fridge_row(self, fridge: Dict):
        row = ctk.CTkFrame(self.fridges_frame, fg_color="#111b2e", corner_radius=10)
        row.pack(fill="x", pady=3)
        row.grid_columnconfigure(0, weight=2)
        row.grid_columnconfigure(1, weight=1)
        row.grid_columnconfigure(2, weight=1)
        row.grid_columnconfigure(3, weight=1)
        row.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(row, text=f"❄️ {fridge.get('device_name') or '-'}", font=("Segoe UI", 12), anchor="w").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkLabel(row, text=fridge.get("location") or "-", text_color="#cbd5e1", anchor="w").grid(row=0, column=1, padx=10, pady=10, sticky="w")

        latest_temperature = fridge.get("latest_temperature_c")
        temp_text = f"{latest_temperature}°C" if latest_temperature is not None else "No data"
        ctk.CTkLabel(row, text=temp_text, text_color="#f8fafc", anchor="w").grid(row=0, column=2, padx=10, pady=10, sticky="w")

        status = (fridge.get("latest_status") or "normal").lower()
        status_color = "#0f766e" if status == "normal" else "#b91c1c"
        status_text = "Normal" if status == "normal" else "Alert"
        make_badge(row, status_text, status_color, "#f8fafc", 90, 24).grid(row=0, column=3, padx=8, pady=10)

        last_update = fridge.get("latest_recorded_at") or "Not yet recorded"
        ctk.CTkLabel(row, text=str(last_update), text_color="#8fa2c9", anchor="w").grid(row=0, column=4, padx=10, pady=10, sticky="w")

    def _register_fridge(self):
        try:
            device_name = self.register_fields["device_name"].get().strip()
            if not device_name:
                self._show_status("Device name is required", "error")
                return

            room_name = self.room_var.get().strip()
            room_id = self.room_lookup.get(room_name) if room_name in self.room_lookup else None
            min_temp = self._parse_optional_float(self.register_fields["min_temperature"].get())
            max_temp = self._parse_optional_float(self.register_fields["max_temperature"].get())
            success, message, fridge_id = self.fridge_service.register_fridge(
                device_name=device_name,
                device_code=self.register_fields["device_code"].get().strip() or None,
                location=self.register_fields["location"].get().strip() or None,
                room_id=room_id,
                connection_type=self.connection_var.get().strip() or "wifi",
                endpoint_url=self.register_fields["endpoint_url"].get().strip() or None,
                min_temperature=min_temp,
                max_temperature=max_temp,
                notes=self.register_fields["notes"].get().strip() or None,
                is_active=self.active_var.get(),
            )
            if success:
                self._clear_register_form()
                self._load_fridges()
                self._show_status(message, "success")
            else:
                self._show_status(message, "error")
        except Exception as exc:
            logger.error("Failed to register fridge: %s", exc)
            self._show_status(str(exc), "error")

    def _record_reading(self):
        try:
            fridge_name = self.fridge_var.get().strip()
            fridge_id = self.fridge_lookup.get(fridge_name)
            if not fridge_id:
                self._show_status("Select a fridge before recording a reading", "error")
                return

            temperature_text = self.temperature_entry.get().strip()
            if not temperature_text:
                self._show_status("Temperature is required", "error")
                return

            success, message, reading_id = self.fridge_service.record_temperature(
                fridge_id=fridge_id,
                temperature_c=float(temperature_text),
                source=self.source_var.get().strip() or "wifi",
                notes=self.reading_notes_entry.get().strip() or None,
            )
            if success:
                self.temperature_entry.delete(0, "end")
                self.reading_notes_entry.delete(0, "end")
                self._load_fridges()
                self._show_status(message, "success")
            else:
                self._show_status(message, "error")
        except ValueError:
            self._show_status("Temperature must be numeric", "error")
        except Exception as exc:
            logger.error("Failed to record fridge reading: %s", exc)
            self._show_status(str(exc), "error")

    def _test_wifi_connection(self):
        fridge_id = self._selected_fridge_id()
        if not fridge_id:
            self._show_status("Select a fridge before testing Wi-Fi", "error")
            return
        success, message, details = self.fridge_service.check_wifi_connection(fridge_id=fridge_id)
        if success and details:
            detail_text = str(details)
            if len(detail_text) > 80:
                detail_text = detail_text[:77] + "..."
            self._show_status(f"{message}. Response: {detail_text}", "success")
            return
        self._show_status(message, "success" if success else "error")

    def _sync_from_wifi_endpoint(self):
        fridge_id = self._selected_fridge_id()
        if not fridge_id:
            self._show_status("Select a fridge before syncing from Wi-Fi", "error")
            return
        success, message, _reading_id = self.fridge_service.pull_temperature_from_wifi_endpoint(fridge_id=fridge_id)
        if success:
            self._load_fridges()
        self._show_status(message, "success" if success else "error")

    def _selected_fridge_id(self) -> Optional[int]:
        fridge_name = self.fridge_var.get().strip()
        return self.fridge_lookup.get(fridge_name)

    def _clear_register_form(self):
        for key, entry in self.register_fields.items():
            entry.delete(0, "end")
        self.room_var.set("")
        self.connection_var.set("wifi")
        self.active_var.set(True)

    def _parse_optional_float(self, value: Optional[str]):
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        return float(value)

    def _show_status(self, message: str, kind: str):
        self.status_label.configure(
            text=message,
            text_color="#fca5a5" if kind == "error" else "#86efac",
        )
