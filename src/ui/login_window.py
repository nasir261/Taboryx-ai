"""
Login Window
User authentication interface
"""

import customtkinter as ctk
import logging
from typing import Callable, Optional
from src.services.auth_service import AuthenticationService
from src.services.saved_credentials_service import SavedCredentialsService
from src.services.time_sync_service import get_time_sync_service
from src.models.models import User
from src.config import BUTTON_HEIGHT, BUTTON_WIDTH, TITLE_FONT, LABEL_FONT

logger = logging.getLogger(__name__)


class LoginWindow(ctk.CTkFrame):
    """Login window frame"""

    def __init__(self, parent, login_callback: Callable, initial_message: Optional[str] = None):
        super().__init__(parent)
        self.parent = parent
        self.login_callback = login_callback
        self.initial_message = initial_message
        self.auth_service = AuthenticationService()
        self.saved_credentials_service = SavedCredentialsService()
        self.time_sync_service = get_time_sync_service()
        self.save_password_var = ctk.BooleanVar(value=False)
        self._current_time_job = None
        
        self._create_widgets()
        self._load_saved_credentials()
        self._schedule_current_time_update()

    def _create_widgets(self):
        """Create login UI elements"""
        # Main container
        main_container = ctk.CTkFrame(self)
        main_container.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        title = ctk.CTkLabel(
            main_container,
            text="Taboryx AI",
            font=("Segoe UI", 28, "bold")
        )
        title.pack(pady=20)

        # Subtitle
        subtitle = ctk.CTkLabel(
            main_container,
            text="Prison Healthcare Inventory Management",
            font=LABEL_FONT
        )
        subtitle.pack(pady=10)

        # Username field
        username_label = ctk.CTkLabel(
            main_container,
            text="Username:",
            font=LABEL_FONT
        )
        username_label.pack(pady=(20, 5))

        self.username_entry = ctk.CTkEntry(
            main_container,
            width=300,
            placeholder_text="Enter username",
            font=LABEL_FONT
        )
        self.username_entry.pack(pady=5)
        self.username_entry.bind("<Return>", lambda e: self._login())

        # Password field
        password_label = ctk.CTkLabel(
            main_container,
            text="Password:",
            font=LABEL_FONT
        )
        password_label.pack(pady=(15, 5))

        self.password_entry = ctk.CTkEntry(
            main_container,
            width=300,
            placeholder_text="Enter password",
            show="*",
            font=LABEL_FONT
        )
        self.password_entry.pack(pady=5)
        self.password_entry.bind("<Return>", lambda e: self._login())

        self.save_password_checkbox = ctk.CTkCheckBox(
            main_container,
            text="Save Password",
            variable=self.save_password_var,
            font=LABEL_FONT,
        )
        self.save_password_checkbox.pack(pady=(8, 6))

        # Error message label
        self.error_label = ctk.CTkLabel(
            main_container,
            text="",
            text_color="red",
            font=LABEL_FONT
        )
        self.error_label.pack(pady=10)

        self.info_label = ctk.CTkLabel(
            main_container,
            text=self.initial_message or "",
            text_color="orange",
            font=LABEL_FONT,
        )
        self.info_label.pack(pady=(0, 6))

        self.current_time_label = ctk.CTkLabel(
            main_container,
            text="Current time: --",
            text_color="lightblue",
            font=LABEL_FONT,
        )
        self.current_time_label.pack(pady=(0, 8))

        # Login button
        login_button = ctk.CTkButton(
            main_container,
            text="Login",
            width=BUTTON_WIDTH,
            height=BUTTON_HEIGHT,
            command=self._login,
            font=LABEL_FONT
        )
        login_button.pack(pady=20)

        # Info text
        info_label = ctk.CTkLabel(
            main_container,
            text="Demo Credentials:\nUsername: admin\nPassword: password123",
            font=("Segoe UI", 9),
            text_color="gray"
        )
        info_label.pack(pady=10)

    def _login(self):
        """Handle login"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self.error_label.configure(text="Please enter username and password")
            return

        # Attempt login
        success, message, user = self.auth_service.login(username, password)

        if success:
            if self.save_password_var.get():
                saved, save_message = self.saved_credentials_service.save_credentials(username, password)
                if not saved:
                    logger.error(f"Failed to save credentials: {save_message}")
            else:
                cleared, clear_message = self.saved_credentials_service.clear_credentials()
                if not cleared:
                    logger.error(f"Failed to clear saved credentials: {clear_message}")

            self.error_label.configure(text="", text_color="red")
            self.info_label.configure(text="")
            if self._current_time_job:
                try:
                    self.after_cancel(self._current_time_job)
                except Exception:
                    pass
                self._current_time_job = None
            self.login_callback(user)
        else:
            self.error_label.configure(text=message, text_color="red")
            self.password_entry.delete(0, "end")
            logger.warning(f"Failed login attempt: {message}")

    def _load_saved_credentials(self):
        username, password, is_saved = self.saved_credentials_service.load_credentials()
        if not is_saved:
            return

        self.username_entry.delete(0, "end")
        self.username_entry.insert(0, username)
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, password)
        self.save_password_var.set(True)

    def _schedule_current_time_update(self):
        self._update_current_time()

    def _update_current_time(self):
        if not hasattr(self, "current_time_label"):
            return
        self.current_time_label.configure(text=f"Current time: {self.time_sync_service.get_date_time_signature()}")
        self._current_time_job = self.after(1000, self._update_current_time)
