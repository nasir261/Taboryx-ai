"""
Taboryx AI - Configuration Module
Centralized configuration for the application
"""

import os
import sys
from pathlib import Path
from enum import Enum

# Application info
APP_NAME = "Taboryx AI"
APP_VERSION = "0.1.0"
APP_AUTHOR = "Taboryx Development Team"


def _resolve_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_NAME
        return Path.home() / APP_NAME
    return Path(__file__).resolve().parent.parent


# Paths
BASE_DIR = _resolve_base_dir()
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "Taboryx.db"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
DB_TIMEOUT = 30

# UI Configuration
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
WINDOW_TITLE = f"{APP_NAME} v{APP_VERSION}"
THEME = "dark"  # 'dark' or 'light'
COLOR_THEME = "blue"

# UI Constants
BUTTON_HEIGHT = 40
BUTTON_WIDTH = 120
LABEL_FONT = ("Segoe UI", 12)
TITLE_FONT = ("Segoe UI", 18, "bold")
HEADER_FONT = ("Segoe UI", 14, "bold")

# Security
PASSWORD_MIN_LENGTH = 8
SESSION_TIMEOUT_MINUTES = 15
SESSION_TIMEOUT_WARNING_SECONDS = 60
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
ENCRYPTION_KEY_PATH = DATA_DIR / "app_encryption.key"
ENFORCE_HTTPS_ONLY = True
TIME_SYNC_ENABLED_DEFAULT = True
TIME_SYNC_INTERVAL_MINUTES = 60
TIME_SYNC_API_URL = "https://worldtimeapi.org/api/timezone/Etc/UTC"
TIME_SYNC_FALLBACK_API_URLS = (
    "https://timeapi.io/api/Time/current/zone?timeZone=UTC",
    "https://worldclockapi.com/api/json/utc/now",
)
TIME_SYNC_FALLBACK_DATE_URLS = (
    "https://www.google.com/generate_204",
    "https://www.microsoft.com",
)
TIME_SYNC_TIMEOUT_SECONDS = 5
MOBILE_API_ENABLED_DEFAULT = True
MOBILE_API_HOST = "0.0.0.0"
MOBILE_API_PORT = 8000

# App settings encryption policy
SENSITIVE_APP_SETTING_PREFIXES = ("security.", "integration.", "api.", "smtp.")

# Stock Levels
CRITICAL_STOCK_PERCENTAGE = 10
LOW_STOCK_PERCENTAGE = 25
EXPIRY_WARNING_DAYS = [30, 60, 90]
MAJOR_STOCK_ADJUSTMENT_CONFIRM_THRESHOLD = 20
CLINICAL_SAFETY_CHECK_NOTICE = (
    "Check the physical product, packaging, integrity, batch number and expiry date before clinical use. "
    "The electronic inventory supports but does not replace the final physical safety check."
)

# Barcode Scanner
BARCODE_SCANNER_TIMEOUT = 5000  # milliseconds

# Role-Based Permissions
class UserRole(Enum):
    ADMINISTRATOR = "administrator"
    PHARMACY_STAFF = "pharmacy_staff"
    DOCTOR = "doctor"
    NURSE = "nurse"
    HEALTHCARE_ASSISTANT = "healthcare_assistant"
    MANAGER = "manager"

# Permission mappings
ROLE_PERMISSIONS = {
    UserRole.ADMINISTRATOR: [
        "manage_users",
        "view_reports",
        "edit_inventory",
        "delete_records",
        "configure_system",
        "view_audit_log"
    ],
    UserRole.PHARMACY_STAFF: [
        "add_stock",
        "adjust_stock",
        "view_purchasing_reports",
        "receive_expiry_alerts",
        "view_inventory"
    ],
    UserRole.DOCTOR: [
        "view_stock",
        "record_item_usage",
        "report_shortages",
        "view_inventory"
    ],
    UserRole.NURSE: [
        "record_stock_usage",
        "view_expiry_dates",
        "perform_audits",
        "view_inventory"
    ],
    UserRole.HEALTHCARE_ASSISTANT: [
        "view_stock",
        "record_item_usage"
    ],
    UserRole.MANAGER: [
        "view_reports",
        "view_inventory",
        "view_audit_log"
    ]
}

# Stock Movement Types
class StockMovementType(Enum):
    RECEIVED = "received"
    USED = "used"
    ISSUED = "issued"
    TRANSFERRED = "transferred"
    QUARANTINED = "quarantined"
    RETURNED = "returned"
    EXPIRED = "expired"
    DISPOSED = "disposed"
    ADJUSTED = "adjusted"
    LOST = "lost"
    DAMAGED = "damaged"

# Item Categories
ITEM_CATEGORIES = [
    "Medicines",
    "Emergency Drugs",
    "Dressings",
    "Cannulas",
    "Needles",
    "Syringes",
    "Catheters",
    "Blood Bottles",
    "Vaccines",
    "Medical Devices",
    "Resuscitation Equipment",
    "PPE",
    "Controlled Drugs",
    "Dental Supplies",
    "Laboratory Supplies",
    "Cleaning Products",
    "Office Supplies"
]

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Reporting
REPORT_FORMATS = ["PDF", "Excel", "CSV"]
EXPORT_DIR = BASE_DIR / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Backup
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Attachments
ATTACHMENTS_DIR = DATA_DIR / "attachments"
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Saved login credentials
SAVED_CREDENTIALS_PATH = DATA_DIR / "saved_credentials.json"
