"""
Session Timeout Service
Tracks inactivity windows and remaining session time.
"""

from datetime import datetime, timedelta
from typing import Optional


class SessionTimeoutService:
    """In-memory inactivity timer for logged-in sessions."""

    def __init__(self, timeout_minutes: int):
        if timeout_minutes <= 0:
            raise ValueError("timeout_minutes must be greater than zero")
        self.timeout_delta = timedelta(minutes=timeout_minutes)
        self.last_activity_at = datetime.now()

    def record_activity(self, when: Optional[datetime] = None):
        self.last_activity_at = when or datetime.now()

    def get_seconds_remaining(self, now: Optional[datetime] = None) -> int:
        current_time = now or datetime.now()
        expires_at = self.last_activity_at + self.timeout_delta
        seconds = int((expires_at - current_time).total_seconds())
        return max(0, seconds)

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        return self.get_seconds_remaining(now) <= 0

    def is_warning_threshold_reached(self, warning_seconds: int, now: Optional[datetime] = None) -> bool:
        if warning_seconds <= 0:
            raise ValueError("warning_seconds must be greater than zero")
        return self.get_seconds_remaining(now) <= warning_seconds
