"""
Microphone diagnostics and selector view.
"""

import logging
import threading

import customtkinter as ctk

from src.services.voice_typing_service import get_voice_typing_service

logger = logging.getLogger(__name__)


class MicrophoneSettingsView(ctk.CTkFrame):
    """Frame for microphone selection and diagnostics."""

    WINDOWS_DEFAULT_OPTION = "Windows Default"

    def __init__(self, parent):
        super().__init__(parent)
        self.voice_typing_service = get_voice_typing_service()
        self.device_options = []
        self.selected_device_var = ctk.StringVar(value="")

        self._setup_ui()
        self._load_microphones()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="Microphone Settings", font=("Arial", 16, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(top_frame, text="Refresh", width=100, fg_color="gray", command=self._load_microphones).pack(side="right", padx=5)

        self.status_label = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color="gray")
        self.status_label.pack(anchor="w", padx=14, pady=(0, 8))

        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            info_frame,
            text=(
                "Select the Windows microphone that the app should use for voice typing. "
                "If you want to use an iPhone microphone, first expose it to Windows as an input device, "
                "then select it here. Speech recognition uses an online recognition service, "
                "so the PC also needs an active internet connection when dictating."
            ),
            wraplength=900,
            justify="left",
            font=("Arial", 11),
        ).pack(anchor="w", padx=10, pady=10)

        selector_frame = ctk.CTkFrame(self)
        selector_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(selector_frame, text="Selected Microphone", font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        self.microphone_combo = ctk.CTkComboBox(selector_frame, values=[""], variable=self.selected_device_var, state="readonly", width=620)
        self.microphone_combo.pack(anchor="w", padx=10, pady=(0, 10))

        button_row = ctk.CTkFrame(selector_frame, fg_color="transparent")
        button_row.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(button_row, text="Save Selection", width=140, command=self._save_selection).pack(side="left", padx=5)
        ctk.CTkButton(button_row, text="Use Windows Default", width=160, fg_color="gray", command=self._clear_selection).pack(side="left", padx=5)
        ctk.CTkButton(button_row, text="Test Microphone", width=140, command=self._test_microphone).pack(side="left", padx=5)

        diagnostics_frame = ctk.CTkFrame(self)
        diagnostics_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(diagnostics_frame, text="Diagnostics", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        self.diagnostics_text = ctk.CTkTextbox(diagnostics_frame, height=260)
        self.diagnostics_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _load_microphones(self):
        diagnostics = self.voice_typing_service.get_microphone_diagnostics()
        devices = diagnostics["devices"]
        self.device_options = [self._format_device(device["index"], device["name"]) for device in devices]
        combo_values = [self.WINDOWS_DEFAULT_OPTION] + self.device_options if self.device_options else [self.WINDOWS_DEFAULT_OPTION]
        self.microphone_combo.configure(values=combo_values)

        selected_value = self.WINDOWS_DEFAULT_OPTION
        if diagnostics["selected_index"] is not None:
            selected_value = self._format_device(diagnostics["selected_index"], diagnostics["selected_name"] or f"Device {diagnostics['selected_index']}")
        self.microphone_combo.set(selected_value)

        self._render_diagnostics(diagnostics)
        if diagnostics["available"] and diagnostics["devices_available"]:
            self.status_label.configure(text=diagnostics["devices_message"], text_color="green")
        else:
            self.status_label.configure(text=diagnostics["devices_message"] or diagnostics["availability_message"], text_color="red")

    def _save_selection(self):
        selection = self.microphone_combo.get().strip()
        if not selection or selection == self.WINDOWS_DEFAULT_OPTION:
            self._clear_selection()
            return

        device_index = self._parse_prefixed_id(selection)
        device_name = selection.split(" - ", 1)[1] if " - " in selection else selection
        if device_index is None:
            self.status_label.configure(text="Please select a valid microphone.", text_color="red")
            return

        self.voice_typing_service.set_selected_microphone(device_index, device_name)
        self.status_label.configure(text=f"Microphone saved: {device_name}", text_color="green")
        self._load_microphones()

    def _clear_selection(self):
        self.voice_typing_service.set_selected_microphone(None)
        self.microphone_combo.set(self.WINDOWS_DEFAULT_OPTION)
        self.status_label.configure(text="Voice typing will now use the Windows default microphone.", text_color="green")
        self._load_microphones()

    def _test_microphone(self):
        self.status_label.configure(text="Listening for microphone test...", text_color="gray")

        def worker():
            selected_index = self._parse_prefixed_id(self.microphone_combo.get().strip())
            success, message, text = self.voice_typing_service.capture_text(timeout=5, phrase_time_limit=8, device_index=selected_index)
            self.after(0, lambda: self._finish_microphone_test(success, message, text))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_microphone_test(self, success: bool, message: str, text: str):
        color = "green" if success else "red"
        self.status_label.configure(text=message, text_color=color)
        if success and text:
            self.diagnostics_text.insert("end", f"\nTest transcript: {text}\n")
            self.diagnostics_text.see("end")

    def _render_diagnostics(self, diagnostics: dict):
        self.diagnostics_text.delete("1.0", "end")
        lines = [
            f"Voice typing availability: {diagnostics['availability_message']}",
            f"Microphone detection: {diagnostics['devices_message']}",
            f"Selected microphone: {diagnostics['selected_name'] or 'Windows default'}",
            f"Python runtime: {diagnostics['python_executable']} ({diagnostics['python_version']})",
            "",
            "Detected input devices:",
        ]
        if diagnostics.get("speech_import_error"):
            lines.insert(3, f"Speech import error: {diagnostics['speech_import_error']}")
        for device in diagnostics["devices"]:
            lines.append(f"- {device['index']}: {device['name']}")
        if not diagnostics["devices"]:
            lines.append("- None")
        self.diagnostics_text.insert("1.0", "\n".join(lines))

    @staticmethod
    def _format_device(index: int, name: str) -> str:
        return f"{index} - {name}"

    @staticmethod
    def _parse_prefixed_id(value: str):
        if not value:
            return None
        prefix = value.split(" - ", 1)[0].strip()
        return int(prefix) if prefix.isdigit() else None
