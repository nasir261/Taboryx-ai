"""
Reusable voice-typing UI helpers for dialogs.
"""

import logging
import threading

import customtkinter as ctk

from src.services.voice_typing_service import get_voice_typing_service

logger = logging.getLogger(__name__)


class VoiceTypingMixin:
    """Mixin that adds microphone-based dictation buttons to text fields."""

    VOICE_BUTTON_TEXT = "🎤"

    def _initialize_voice_typing(self):
        self.voice_typing_service = get_voice_typing_service()

    def _create_voice_field(self, parent, label: str, multiline: bool = False, required: bool = False, width: int = 400):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=5)

        label_text = label + (" *" if required else "")
        ctk.CTkLabel(frame, text=label_text, font=("Arial", 11, "bold")).pack(anchor="w")

        input_frame = ctk.CTkFrame(frame, fg_color="transparent")
        input_frame.pack(fill="x", pady=5)

        if multiline:
            field = ctk.CTkTextbox(input_frame, height=80, width=width)
        else:
            field = ctk.CTkEntry(input_frame, width=width)
        field.pack(side="left", fill="x", expand=True)

        button = ctk.CTkButton(
            input_frame,
            text=self.VOICE_BUTTON_TEXT,
            width=48,
            command=lambda current_field=field, current_button=None: None,
        )
        button.configure(command=lambda current_field=field, current_button=button: self._start_voice_typing(current_field, current_button))
        button.pack(side="left", padx=(8, 0))
        return field

    def _create_inline_voice_field(self, parent, label: str, width: int = 100):
        frame = ctk.CTkFrame(parent)
        frame.pack(side="left", padx=10)

        ctk.CTkLabel(frame, text=label + ":", font=("Arial", 10)).pack(anchor="w")
        input_frame = ctk.CTkFrame(frame, fg_color="transparent")
        input_frame.pack(fill="x", pady=3)

        field = ctk.CTkEntry(input_frame, width=width)
        field.pack(side="left")

        button = ctk.CTkButton(
            input_frame,
            text=self.VOICE_BUTTON_TEXT,
            width=42,
            command=lambda current_field=field, current_button=None: None,
        )
        button.configure(command=lambda current_field=field, current_button=button: self._start_voice_typing(current_field, current_button))
        button.pack(side="left", padx=(6, 0))
        return field

    def _start_voice_typing(self, widget, button):
        available, message = self.voice_typing_service.is_available()
        if not available:
            self._set_voice_typing_status(message, "red")
            return

        self._set_voice_typing_status("Listening for voice input...", "gray")
        button.configure(state="disabled", text="...")

        def worker():
            success, result_message, captured_text = self.voice_typing_service.capture_text(timeout=8, phrase_time_limit=15)
            self.after(0, lambda: self._finish_voice_typing(widget, button, success, result_message, captured_text))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_voice_typing(self, widget, button, success: bool, message: str, captured_text: str):
        button.configure(state="normal", text=self.VOICE_BUTTON_TEXT)
        if success and captured_text:
            self._append_voice_text(widget, captured_text)
            self._set_voice_typing_status("Voice input inserted.", "green")
        else:
            self._set_voice_typing_status(message, "red")

    @staticmethod
    def _append_voice_text(widget, captured_text: str):
        if isinstance(widget, ctk.CTkTextbox):
            existing = widget.get("1.0", "end").strip()
            if existing:
                widget.insert("end", "\n" + captured_text)
            else:
                widget.insert("1.0", captured_text)
            return

        existing = widget.get().strip()
        new_value = f"{existing} {captured_text}".strip() if existing else captured_text
        widget.delete(0, "end")
        widget.insert(0, new_value)

    def _set_voice_typing_status(self, message: str, color: str):
        status_label = getattr(self, "status_label", None)
        if status_label is not None:
            status_label.configure(text=message, text_color=color)
        logger.info(message)
