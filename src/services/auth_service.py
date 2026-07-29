"""
Authentication Service
Handles user login, password management, and session management
"""

import logging
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from src.database.db import get_database
from src.models.models import User
from src.config import PASSWORD_MIN_LENGTH, MAX_LOGIN_ATTEMPTS, LOCKOUT_DURATION_MINUTES, UserRole

logger = logging.getLogger(__name__)


class AuthenticationService:
    """Service for user authentication and session management"""

    def __init__(self):
        self.db = get_database()

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        if len(password) < PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
        
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Fetch user by username"""
        try:
            user_dict = self.db.fetch_one(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            )
            if user_dict:
                return self._dict_to_user(user_dict)
            return None
        except Exception as e:
            logger.error(f"Error fetching user by username: {e}")
            return None

    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """
        Authenticate user and return (success, message, user)
        """
        try:
            user = self.get_user_by_username(username)
            
            if not user:
                logger.warning(f"Login attempt with non-existent username: {username}")
                return False, "Invalid username or password", None

            if not user.is_active:
                logger.warning(f"Login attempt with inactive user: {username}")
                return False, "User account is inactive", None

            # Check if user is locked out
            if user.lockout_until and datetime.now() < user.lockout_until:
                remaining = (user.lockout_until - datetime.now()).seconds // 60
                return False, f"Account is locked. Try again in {remaining} minutes", None

            # Verify password
            if not self.verify_password(password, user.password_hash):
                # Increment failed login attempts
                self.db.update(
                    "users",
                    {"failed_login_attempts": user.failed_login_attempts + 1},
                    "id = ?",
                    (user.id,)
                )
                
                # Lock account if max attempts exceeded
                if user.failed_login_attempts + 1 >= MAX_LOGIN_ATTEMPTS:
                    lockout_time = datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                    self.db.update(
                        "users",
                        {"lockout_until": lockout_time},
                        "id = ?",
                        (user.id,)
                    )
                    logger.warning(f"Account locked due to failed attempts: {username}")
                    return False, f"Account locked due to multiple failed attempts. Try again later", None
                
                logger.warning(f"Failed login attempt for user: {username}")
                return False, "Invalid username or password", None

            # Successful login - reset failed attempts
            self.db.update(
                "users",
                {"failed_login_attempts": 0, "lockout_until": None},
                "id = ?",
                (user.id,)
            )
            
            logger.info(f"Successful login: {username}")
            return True, "Login successful", user

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, "An error occurred during login", None

    def create_user(self, username: str, email: str, password: str, 
                   full_name: str, role: str) -> Tuple[bool, str, Optional[int]]:
        """
        Create a new user account
        """
        try:
            # Validate inputs
            if not username or len(username) < 3:
                return False, "Username must be at least 3 characters", None

            if not email or '@' not in email:
                return False, "Invalid email address", None

            # Check if user already exists
            existing_user = self.get_user_by_username(username)
            if existing_user:
                return False, "Username already exists", None

            # Hash password
            password_hash = self.hash_password(password)

            # Create user
            user_id = self.db.insert(
                "users",
                {
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                    "full_name": full_name,
                    "role": role,
                    "is_active": True,
                    "failed_login_attempts": 0
                }
            )

            logger.info(f"New user created: {username} (ID: {user_id})")
            return True, "User created successfully", user_id

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False, f"Error creating user: {str(e)}", None

    def change_password(self, user_id: int, old_password: str, 
                       new_password: str) -> Tuple[bool, str]:
        """
        Change user password
        """
        try:
            user = self._get_user_by_id(user_id)
            if not user:
                return False, "User not found"

            # Verify old password
            if not self.verify_password(old_password, user.password_hash):
                return False, "Current password is incorrect"

            # Hash new password
            new_password_hash = self.hash_password(new_password)

            # Update password
            self.db.update(
                "users",
                {"password_hash": new_password_hash},
                "id = ?",
                (user_id,)
            )

            logger.info(f"Password changed for user ID: {user_id}")
            return True, "Password changed successfully"

        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False, f"Error changing password: {str(e)}"

    def reset_password(self, user_id: int, new_password: str) -> Tuple[bool, str]:
        """
        Reset user password (admin function)
        """
        try:
            user = self._get_user_by_id(user_id)
            if not user:
                return False, "User not found"

            # Hash new password
            password_hash = self.hash_password(new_password)

            # Update password
            self.db.update(
                "users",
                {"password_hash": password_hash, "failed_login_attempts": 0, "lockout_until": None},
                "id = ?",
                (user_id,)
            )

            logger.info(f"Password reset for user ID: {user_id}")
            return True, "Password reset successfully"

        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return False, f"Error resetting password: {str(e)}"

    def get_all_users(self) -> List[User]:
        """Fetch all users for administration."""
        try:
            rows = self.db.fetch_all("SELECT * FROM users ORDER BY username")
            return [self._dict_to_user(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            return []

    def set_user_active(self, user_id: int, is_active: bool) -> Tuple[bool, str]:
        """Activate or deactivate a user."""
        try:
            user = self._get_user_by_id(user_id)
            if not user:
                return False, "User not found"

            rows = self.db.update(
                "users",
                {"is_active": bool(is_active), "updated_at": datetime.now()},
                "id = ?",
                (user_id,),
            )
            if rows <= 0:
                return False, "User not found"
            return True, "User updated successfully"
        except Exception as e:
            logger.error(f"Error updating user active status: {e}")
            return False, f"Error updating user: {str(e)}"

    def update_user_role(self, user_id: int, role: str) -> Tuple[bool, str]:
        """Update role for a user."""
        try:
            user = self._get_user_by_id(user_id)
            if not user:
                return False, "User not found"

            normalized_role = (role or "").strip().lower()
            valid_roles = {member.value for member in UserRole}
            if normalized_role not in valid_roles:
                return False, "Invalid role"

            rows = self.db.update(
                "users",
                {"role": normalized_role, "updated_at": datetime.now()},
                "id = ?",
                (user_id,),
            )
            if rows <= 0:
                return False, "User not found"
            return True, "User role updated successfully"
        except Exception as e:
            logger.error(f"Error updating user role: {e}")
            return False, f"Error updating user role: {str(e)}"

    def _get_user_by_id(self, user_id: int) -> Optional[User]:
        """Fetch user by ID"""
        try:
            user_dict = self.db.fetch_one(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            if user_dict:
                return self._dict_to_user(user_dict)
            return None
        except Exception as e:
            logger.error(f"Error fetching user by ID: {e}")
            return None

    @staticmethod
    def _dict_to_user(user_dict: dict) -> User:
        """Convert database row to User object"""
        return User(
            id=user_dict.get('id'),
            username=user_dict.get('username', ''),
            email=user_dict.get('email', ''),
            password_hash=user_dict.get('password_hash', ''),
            full_name=user_dict.get('full_name', ''),
            role=user_dict.get('role', ''),
            is_active=bool(user_dict.get('is_active', True)),
            failed_login_attempts=user_dict.get('failed_login_attempts', 0),
            lockout_until=user_dict.get('lockout_until'),
            created_at=user_dict.get('created_at'),
            updated_at=user_dict.get('updated_at')
        )
