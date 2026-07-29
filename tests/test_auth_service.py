"""
Tests for authentication service user-management operations.
"""

import tempfile
from pathlib import Path

from src.database.db import get_database, init_database
from src.services.auth_service import AuthenticationService


class TestAuthenticationService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_auth_service.db"
        init_database(self.db_path, seed_default_admin=True)
        self.auth_service = AuthenticationService()

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_get_all_users_returns_created_users(self):
        success, _, _ = self.auth_service.create_user(
            username="admin1",
            email="admin1@example.com",
            password="password123",
            full_name="Admin One",
            role="administrator",
        )
        assert success
        success, _, _ = self.auth_service.create_user(
            username="doctor1",
            email="doctor1@example.com",
            password="password123",
            full_name="Doctor One",
            role="doctor",
        )
        assert success

        users = self.auth_service.get_all_users()
        usernames = [user.username for user in users]
        assert "admin1" in usernames
        assert "doctor1" in usernames

    def test_set_user_active_toggles_account_state(self):
        success, _, user_id = self.auth_service.create_user(
            username="activeuser",
            email="active@example.com",
            password="password123",
            full_name="Active User",
            role="nurse",
        )
        assert success

        success, message = self.auth_service.set_user_active(user_id, False)
        assert success
        assert message == "User updated successfully"

        user = self.auth_service._get_user_by_id(user_id)
        assert user is not None
        assert not user.is_active

    def test_update_user_role_validates_role(self):
        success, _, user_id = self.auth_service.create_user(
            username="roleuser",
            email="role@example.com",
            password="password123",
            full_name="Role User",
            role="doctor",
        )
        assert success

        success, message = self.auth_service.update_user_role(user_id, "manager")
        assert success
        assert message == "User role updated successfully"

        user = self.auth_service._get_user_by_id(user_id)
        assert user is not None
        assert user.role == "manager"

        success, message = self.auth_service.update_user_role(user_id, "invalid-role")
        assert not success
        assert message == "Invalid role"

    def test_init_database_creates_default_admin_user(self):
        success, message, user = self.auth_service.login("admin", "password123")
        assert success
        assert message == "Login successful"
        assert user is not None
        assert user.username == "admin"
        assert user.role == "administrator"
