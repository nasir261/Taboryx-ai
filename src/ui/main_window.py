"""
Main Window
CustomTkinter main application window with navigation and theme support
"""

import customtkinter as ctk
import logging
import socket
from http.server import ThreadingHTTPServer
from threading import Thread
from typing import Optional
from src.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, THEME, COLOR_THEME,
    BUTTON_HEIGHT, BUTTON_WIDTH, TITLE_FONT, LABEL_FONT,
    SESSION_TIMEOUT_MINUTES, SESSION_TIMEOUT_WARNING_SECONDS, TIME_SYNC_INTERVAL_MINUTES,
    MOBILE_API_ENABLED_DEFAULT, MOBILE_API_HOST, MOBILE_API_PORT,
)
from src.models.models import User
from src.database.db import get_database
from src.ui.login_window import LoginWindow
from src.ui.dashboard import Dashboard
from src.api.server import MediStockAPIHandler
from src.services.backup_service import BackupService
from src.services.session_timeout_service import SessionTimeoutService
from src.services.time_sync_service import get_time_sync_service

logger = logging.getLogger(__name__)


class MainWindow:
    """Main application window"""

    AUTO_BACKUP_CHECK_INTERVAL_MS = 60_000
    TIME_SYNC_INTERVAL_MS = TIME_SYNC_INTERVAL_MINUTES * 60_000

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        try:
            self.root.state("zoomed")
        except Exception:
            self.root.attributes("-zoomed", True)
        
        # Set theme
        ctk.set_appearance_mode(THEME)
        ctk.set_default_color_theme(COLOR_THEME)
        
        self.current_user: Optional[User] = None
        self.db = get_database()
        self.db.clear_audit_user()
        self.current_frame = None
        self.backup_service = BackupService()
        self.auto_backup_job = None
        self.time_sync_service = get_time_sync_service()
        self.time_sync_job = None
        self.time_sync_status_message = "pending"
        self.session_timeout_service: Optional[SessionTimeoutService] = None
        self.session_timer_job = None
        self.logout_reason = None
        self.session_warning_shown = False
        self.mobile_api_server: Optional[ThreadingHTTPServer] = None
        self.mobile_api_thread: Optional[Thread] = None
        self.mobile_access_status_text = "Mobile LAN: unavailable"
        self.mobile_access_status_color = "red"

        self.root.bind_all("<KeyPress>", self._on_user_activity)
        self.root.bind_all("<ButtonPress>", self._on_user_activity)
        self.root.protocol("WM_DELETE_WINDOW", self._on_app_close)
        
        # Configure grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self._schedule_auto_backup_check()
        self._schedule_time_sync(initial=True)
        self._start_mobile_api_server()
        
        logger.info("Main window initialized")

    def show_login(self):
        """Show login window"""
        self._clear_frame()
        self.current_frame = LoginWindow(self.root, self.on_login_success, initial_message=self.logout_reason)
        self.logout_reason = None
        self.current_frame.pack(fill="both", expand=True)

    def show_dashboard(self, user: User):
        """Show dashboard after successful login"""
        self.current_user = user
        self._start_session_timer()
        self._clear_frame()
        self.current_frame = Dashboard(self.root, user, self.on_logout)
        self.current_frame.pack(fill="both", expand=True)
        self._update_dashboard_time_sync_status()
        self._update_dashboard_mobile_access_status()

    def _clear_frame(self):
        """Clear current frame"""
        if self.current_frame:
            self.current_frame.pack_forget()
            self.current_frame = None

    def on_login_success(self, user: User):
        """Callback for successful login"""
        logger.info(f"User logged in: {user.username}")
        self.db.set_audit_user(user.id)
        self.show_dashboard(user)

    def on_logout(self):
        """Callback for logout"""
        if self.current_user:
            logger.info(f"User logged out: {self.current_user.username}")
        self.db.clear_audit_user()
        self.current_user = None
        self._stop_session_timer()
        self.show_login()

    def _on_user_activity(self, _event=None):
        if self.current_user and self.session_timeout_service:
            self.session_timeout_service.record_activity()
            self.session_warning_shown = False
            if isinstance(self.current_frame, Dashboard):
                self.current_frame.set_session_timeout_warning(False)

    def _start_session_timer(self):
        self._stop_session_timer()
        self.session_timeout_service = SessionTimeoutService(SESSION_TIMEOUT_MINUTES)
        self.session_timeout_service.record_activity()
        self.session_warning_shown = False
        self._update_session_timer()

    def _stop_session_timer(self):
        if self.session_timer_job:
            self.root.after_cancel(self.session_timer_job)
            self.session_timer_job = None
        self.session_timeout_service = None
        self.session_warning_shown = False

    def _update_session_timer(self):
        if not self.current_user or not self.session_timeout_service:
            return

        seconds_remaining = self.session_timeout_service.get_seconds_remaining()
        if isinstance(self.current_frame, Dashboard):
            self.current_frame.update_session_timeout(seconds_remaining)
            if self.session_timeout_service.is_warning_threshold_reached(SESSION_TIMEOUT_WARNING_SECONDS):
                if not self.session_warning_shown:
                    self.current_frame.set_session_timeout_warning(True)
                    self.session_warning_shown = True
            elif self.session_warning_shown:
                self.current_frame.set_session_timeout_warning(False)
                self.session_warning_shown = False

        if self.session_timeout_service.is_expired():
            logger.info("User session timed out due to inactivity.")
            self.logout_reason = "You were logged out due to inactivity."
            self.on_logout()
            return

        self.session_timer_job = self.root.after(1000, self._update_session_timer)

    def _schedule_auto_backup_check(self):
        self.auto_backup_job = self.root.after(self.AUTO_BACKUP_CHECK_INTERVAL_MS, self._run_auto_backup_check)

    def _run_auto_backup_check(self):
        success, message, backup_path = self.backup_service.run_scheduled_backup_if_due()
        if success and backup_path:
            logger.info(f"Automatic backup created: {backup_path.name}")
        elif message != "No scheduled backup due":
            logger.error(f"Automatic backup failed: {message}")
        self._schedule_auto_backup_check()

    def _schedule_time_sync(self, initial: bool = False):
        delay = 0 if initial else self.TIME_SYNC_INTERVAL_MS
        self.time_sync_job = self.root.after(delay, self._run_time_sync)

    def _run_time_sync(self):
        success, message = self.time_sync_service.sync_time()
        self.time_sync_status_message = "ok" if success else message
        if success:
            logger.info(message)
        elif message not in {"Time sync is disabled", "Time sync temporarily unavailable; using computer clock", "Time sync unavailable; using computer clock"}:
            logger.warning(message)
        self._update_dashboard_time_sync_status()
        self._schedule_time_sync(initial=False)

    def _update_dashboard_time_sync_status(self):
        if not isinstance(self.current_frame, Dashboard):
            return
        enabled = self.time_sync_service.is_enabled()
        offset_seconds = self.time_sync_service.get_offset_seconds()
        last_sync = self.time_sync_service.get_last_sync_utc()
        last_sync_text = self.time_sync_service.format_utc_datetime(last_sync)
        self.current_frame.update_time_sync_status(
            enabled=enabled,
            offset_seconds=offset_seconds,
            last_sync_text=last_sync_text,
            status_text=self.time_sync_status_message if enabled else "",
        )

    def _start_mobile_api_server(self):
        if not MOBILE_API_ENABLED_DEFAULT:
            self.mobile_access_status_text = "Mobile LAN: disabled"
            self.mobile_access_status_color = "#f59e0b"
            return
        try:
            self.mobile_api_server = ThreadingHTTPServer((MOBILE_API_HOST, MOBILE_API_PORT), MediStockAPIHandler)
            self.mobile_api_thread = Thread(target=self.mobile_api_server.serve_forever, daemon=True)
            self.mobile_api_thread.start()
            lan_ip = self._resolve_lan_ip()
            self.mobile_access_status_text = f"Mobile LAN: http://{lan_ip}:{MOBILE_API_PORT}/"
            self.mobile_access_status_color = "#86efac"
            logger.info("Mobile API LAN access enabled at http://%s:%s/", lan_ip, MOBILE_API_PORT)
        except OSError as exc:
            self.mobile_access_status_text = f"Mobile LAN unavailable: {exc}"
            self.mobile_access_status_color = "red"
            logger.error("Failed to start mobile API server: %s", exc)
        self._update_dashboard_mobile_access_status()

    def _stop_mobile_api_server(self):
        if self.mobile_api_server:
            self.mobile_api_server.shutdown()
            self.mobile_api_server.server_close()
            self.mobile_api_server = None
        self.mobile_api_thread = None

    def _resolve_lan_ip(self) -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
        except OSError:
            pass
        finally:
            sock.close()
        try:
            host_addresses = socket.gethostbyname_ex(socket.gethostname())[2]
        except OSError:
            host_addresses = []
        for address in host_addresses:
            if address and not address.startswith("127."):
                return address
        return "127.0.0.1"

    def _update_dashboard_mobile_access_status(self):
        if isinstance(self.current_frame, Dashboard):
            self.current_frame.update_mobile_access_status(
                status_text=self.mobile_access_status_text,
                color=self.mobile_access_status_color,
            )

    def _on_app_close(self):
        self._stop_session_timer()
        self._stop_mobile_api_server()
        self.root.destroy()

    def run(self):
        """Start the application"""
        try:
            self.show_login()
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Error running application: {e}", exc_info=True)
            raise
