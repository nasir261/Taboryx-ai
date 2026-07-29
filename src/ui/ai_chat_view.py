"""
AI Chat View
Simple assistant panel for stock and purchasing questions.
"""

import customtkinter as ctk

from src.services.ai_chat_service import AIChatService


class AIChatView(ctk.CTkFrame):
    """Chat-like assistant interface."""

    def __init__(self, parent):
        super().__init__(parent)
        self.ai_chat_service = AIChatService()
        self._setup_ui()

    def _setup_ui(self):
        ctk.CTkLabel(self, text="AI Chat Assistant", font=("Arial", 16, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        ctk.CTkLabel(
            self,
            text="Try: Show expired insulin | Which room uses the most gloves? | How many syringes were used this month?",
            font=("Arial", 10),
            text_color="gray",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        self.chat_output = ctk.CTkTextbox(self, height=300)
        self.chat_output.pack(fill="both", expand=True, padx=10, pady=10)
        self.chat_output.insert("end", "Assistant: Hello, ask me about stock, expiry, usage, or purchasing.\n\n")
        self.chat_output.configure(state="disabled")

        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="x", padx=10, pady=(0, 10))

        self.question_entry = ctk.CTkEntry(bottom)
        self.question_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.question_entry.bind("<Return>", lambda _e: self._ask())

        ctk.CTkButton(bottom, text="Ask", width=100, command=self._ask).pack(side="left")

    def _ask(self):
        question = self.question_entry.get().strip()
        if not question:
            return
        self.question_entry.delete(0, "end")

        result = self.ai_chat_service.ask(question)
        self._append_message(f"You: {question}")
        self._append_message(f"Assistant: {result['answer']}")
        if result.get("rows"):
            for row in result["rows"][:8]:
                self._append_message(f"  - {row}")
        self._append_message("")

    def _append_message(self, message: str):
        self.chat_output.configure(state="normal")
        self.chat_output.insert("end", message + "\n")
        self.chat_output.see("end")
        self.chat_output.configure(state="disabled")
