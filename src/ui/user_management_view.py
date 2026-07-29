"""
User Management View
Admin interface for managing user accounts.
"""

import customtkinter as ctk

from src.config import UserRole
from src.services.auth_service import AuthenticationService


class CreateUserDialog(ctk.CTkToplevel):
    """Dialog to create a new user account."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Create User")
        self.geometry("500x460")
        self.resizable(False, False)
        self.grab_set()
        self.result = None

        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        self.username_entry = self._field(frame, "Username")
        self.email_entry = self._field(frame, "Email")
        self.full_name_entry = self._field(frame, "Full Name")
        self.password_entry = self._field(frame, "Password", secret=True)

        ctk.CTkLabel(frame, text="Role", font=("Arial", 11, "bold")).pack(anchor="w", pady=(10, 4))
        self.role_combo = ctk.CTkComboBox(
            frame, values=[role.value for role in UserRole], state="readonly"
        )
        self.role_combo.pack(fill="x")
        self.role_combo.set(UserRole.DOCTOR.value)

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(fill="x", pady=(20, 0))
        ctk.CTkButton(buttons, text="Create", width=120, command=self._confirm).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Cancel", width=120, fg_color="gray", command=self._cancel).pack(side="left", padx=4)

    def _field(self, parent, label: str, secret: bool = False):
        ctk.CTkLabel(parent, text=label, font=("Arial", 11, "bold")).pack(anchor="w", pady=(10, 4))
        entry = ctk.CTkEntry(parent, show="*" if secret else None)
        entry.pack(fill="x")
        return entry

    def _confirm(self):
        self.result = {
            "username": self.username_entry.get().strip(),
            "email": self.email_entry.get().strip(),
            "full_name": self.full_name_entry.get().strip(),
            "password": self.password_entry.get(),
            "role": self.role_combo.get().strip(),
        }
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class UserManagementView(ctk.CTkFrame):
    """Frame for administering users."""

    def __init__(self, parent):
        super().__init__(parent)
        self.auth_service = AuthenticationService()
        self.users = []
        self._setup_ui()
        self._load_users()

    def _setup_ui(self):
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text="User Management", font=("Arial", 16, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Create User", width=120, command=self._create_user).pack(side="right", padx=5)
        ctk.CTkButton(top, text="Refresh", width=100, fg_color="gray", command=self._load_users).pack(side="right", padx=5)

        self.status_label = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color="gray")
        self.status_label.pack(anchor="w", padx=14, pady=(0, 8))

        self.list_frame = ctk.CTkScrollableFrame(self, width=1120, height=560)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self._render_header()

    def _render_header(self):
        header = ctk.CTkFrame(self.list_frame, fg_color="gray20", height=34)
        header.pack(fill="x", padx=5, pady=4)
        header.pack_propagate(False)
        columns = [
            ("Username", 120),
            ("Full Name", 180),
            ("Email", 220),
            ("Role", 130),
            ("Status", 80),
            ("Failed", 60),
            ("Actions", 300),
        ]
        for label, width in columns:
            ctk.CTkLabel(header, text=label, width=width, font=("Arial", 10, "bold")).pack(side="left", padx=3)

    def _load_users(self):
        for widget in self.list_frame.winfo_children()[1:]:
            widget.destroy()

        self.users = self.auth_service.get_all_users()
        if not self.users:
            ctk.CTkLabel(self.list_frame, text="No users found.", text_color="gray").pack(pady=24)
            return

        for index, user in enumerate(self.users):
            self._add_user_row(user, index % 2 == 0)

    def _add_user_row(self, user, alternate: bool):
        bg = "gray15" if alternate else "gray10"
        row = ctk.CTkFrame(self.list_frame, fg_color=bg, height=34)
        row.pack(fill="x", padx=5, pady=2)
        row.pack_propagate(False)

        values = [
            ((user.username or "")[:18], 120),
            ((user.full_name or "")[:28], 180),
            ((user.email or "")[:34], 220),
            ((user.role or "")[:18], 130),
            ("Active" if user.is_active else "Inactive", 80),
            (str(user.failed_login_attempts or 0), 60),
        ]
        for text, width in values:
            ctk.CTkLabel(row, text=text, width=width).pack(side="left", padx=3)

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="left", padx=3)
        ctk.CTkButton(
            actions,
            text="Reset Pass",
            width=90,
            command=lambda uid=user.id: self._reset_password(uid),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            actions,
            text="Deactivate" if user.is_active else "Activate",
            width=90,
            fg_color="orange" if user.is_active else "green",
            command=lambda uid=user.id, active=user.is_active: self._toggle_active(uid, active),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            actions,
            text="Change Role",
            width=95,
            command=lambda uid=user.id: self._change_role(uid),
        ).pack(side="left", padx=2)

    def _create_user(self):
        dialog = CreateUserDialog(self)
        dialog.wait_window()
        if dialog.result is None:
            self.status_label.configure(text="Create user cancelled.", text_color="gray")
            return

        payload = dialog.result
        success, message, _ = self.auth_service.create_user(
            username=payload["username"],
            email=payload["email"],
            password=payload["password"],
            full_name=payload["full_name"],
            role=payload["role"],
        )
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_users()

    def _reset_password(self, user_id: int):
        dialog = ctk.CTkInputDialog(text="Enter new password:", title="Reset User Password")
        new_password = dialog.get_input()
        if new_password is None:
            self.status_label.configure(text="Password reset cancelled.", text_color="gray")
            return

        success, message = self.auth_service.reset_password(user_id, new_password)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_users()

    def _toggle_active(self, user_id: int, currently_active: bool):
        success, message = self.auth_service.set_user_active(user_id, not currently_active)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_users()

    def _change_role(self, user_id: int):
        role_dialog = ctk.CTkInputDialog(
            text=f"Enter role ({', '.join([role.value for role in UserRole])}):",
            title="Change User Role",
        )
        role = role_dialog.get_input()
        if role is None:
            self.status_label.configure(text="Role change cancelled.", text_color="gray")
            return

        success, message = self.auth_service.update_user_role(user_id, role)
        self.status_label.configure(text=message, text_color="green" if success else "red")
        if success:
            self._load_users()
