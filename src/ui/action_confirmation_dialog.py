"""
Reusable confirmation dialog for high-risk actions.
"""

import customtkinter as ctk


class ActionConfirmationDialog(ctk.CTkToplevel):
    """Simple modal dialog that returns True/False for user confirmation."""

    def __init__(self, parent, title: str, message: str):
        super().__init__(parent)
        self.title(title)
        self.geometry("520x220")
        self.resizable(False, False)
        self.grab_set()
        self.result = False

        ctk.CTkLabel(self, text=message, wraplength=480, justify="left", font=("Arial", 11)).pack(
            anchor="w", padx=16, pady=(20, 16)
        )

        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=16, pady=10)
        ctk.CTkButton(button_frame, text="Confirm", width=120, command=self._confirm).pack(side="left", padx=4)
        ctk.CTkButton(button_frame, text="Cancel", width=120, fg_color="gray", command=self._cancel).pack(
            side="left", padx=4
        )

    def _confirm(self):
        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()
