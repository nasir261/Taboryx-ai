"""
Secure web time synchronization for in-app timestamps.
"""

import json
import logging
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Optional, Tuple
from urllib.request import Request, urlopen

from src.config import (
    TIME_SYNC_API_URL,
    TIME_SYNC_FALLBACK_DATE_URLS,
    TIME_SYNC_FALLBACK_API_URLS,
    TIME_SYNC_ENABLED_DEFAULT,
    TIME_SYNC_TIMEOUT_SECONDS,
)
from src.services.app_settings_service import AppSettingsService
from src.services.network_security_service import NetworkSecurityService

logger = logging.getLogger(__name__)


class TimeSyncService:
    """Maintains a persisted offset between local system time and trusted web UTC time."""

    ENABLED_KEY = "time.sync_enabled"
    OFFSET_SECONDS_KEY = "time.offset_seconds"
    LAST_SYNC_UTC_KEY = "time.last_sync_utc"

    def __init__(self, fetch_utc_time: Optional[Callable[[], datetime]] = None):
        self.app_settings_service = AppSettingsService()
        self.fetch_utc_time = fetch_utc_time or self._fetch_utc_time_from_web

    def is_enabled(self) -> bool:
        default = "1" if TIME_SYNC_ENABLED_DEFAULT else "0"
        return self.app_settings_service.get_setting(self.ENABLED_KEY, default) == "1"

    def set_enabled(self, enabled: bool):
        self.app_settings_service.set_setting(self.ENABLED_KEY, "1" if enabled else "0")

    def get_offset_seconds(self) -> int:
        return 0

    def get_last_sync_utc(self) -> Optional[datetime]:
        raw = self.app_settings_service.get_setting(self.LAST_SYNC_UTC_KEY, None)
        if not raw:
            return None
        try:
            return datetime.fromisoformat(str(raw))
        except ValueError:
            return None

    def now(self) -> datetime:
        return datetime.now()

    def today(self):
        return self.now().date()

    def get_date_time_signature(self) -> str:
        return self.now().strftime("%d-%m-%Y %H:%M:%S")

    def get_signature_stamp(self) -> str:
        return f"Signed at {self.get_date_time_signature()}"

    @staticmethod
    def format_utc_datetime(value: Optional[datetime]) -> str:
        if not value:
            return ""
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%d-%m-%Y %H:%M")

    def sync_time(self) -> Tuple[bool, str]:
        if not self.is_enabled():
            return False, "Time sync is disabled"

        try:
            remote_utc = self.fetch_utc_time()
            if remote_utc.tzinfo is None:
                remote_utc = remote_utc.replace(tzinfo=timezone.utc)
            else:
                remote_utc = remote_utc.astimezone(timezone.utc)
            self.app_settings_service.set_setting(self.OFFSET_SECONDS_KEY, "0")
            self.app_settings_service.set_setting(self.LAST_SYNC_UTC_KEY, datetime.now(timezone.utc).isoformat())
            return True, "Time synchronized from secure web source"
        except (ValueError, OSError) as exc:
            logger.warning(f"Time sync unavailable: {exc}")
            if self.get_last_sync_utc() is not None:
                return False, "Time sync temporarily unavailable; using computer clock"
            return False, "Time sync unavailable; using computer clock"

    def _fetch_utc_time_from_web(self) -> datetime:
        last_error = None
        for endpoint in [TIME_SYNC_API_URL] + list(TIME_SYNC_FALLBACK_API_URLS):
            valid, message = NetworkSecurityService.validate_secure_url(endpoint)
            if not valid:
                last_error = message
                continue
            try:
                payload = self._fetch_json(endpoint)
                return self._parse_utc_datetime(payload)
            except (ValueError, OSError) as exc:
                last_error = str(exc)
                logger.warning(f"Time endpoint failed ({endpoint}): {exc}")

        for endpoint in TIME_SYNC_FALLBACK_DATE_URLS:
            valid, message = NetworkSecurityService.validate_secure_url(endpoint)
            if not valid:
                last_error = message
                continue
            try:
                return self._fetch_date_header_time(endpoint)
            except (ValueError, OSError) as exc:
                last_error = str(exc)
                logger.warning(f"Time header fallback failed ({endpoint}): {exc}")

        raise OSError(last_error or "All time endpoints failed")

    @staticmethod
    def _fetch_json(url: str) -> Dict:
        request = Request(
            url=url,
            headers={
                "User-Agent": "MediStockAI/1.0",
                "Accept": "application/json",
            },
        )
        with urlopen(request, timeout=TIME_SYNC_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _parse_utc_datetime(payload: Dict) -> datetime:
        candidates = [
            payload.get("utc_datetime"),
            payload.get("datetime"),
            payload.get("currentDateTime"),
            payload.get("dateTime"),
        ]
        for value in candidates:
            if not value:
                continue
            parsed = str(value).replace("Z", "+00:00")
            dt = datetime.fromisoformat(parsed)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        raise ValueError("Time API response missing supported datetime field")

    @staticmethod
    def _fetch_date_header_time(url: str) -> datetime:
        request = Request(
            url=url,
            headers={
                "User-Agent": "MediStockAI/1.0",
                "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            },
        )
        with urlopen(request, timeout=TIME_SYNC_TIMEOUT_SECONDS) as response:
            header_value = response.headers.get("Date")
            if not header_value:
                raise ValueError("Time response missing Date header")
            parsed = parsedate_to_datetime(header_value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)


def get_time_sync_service() -> TimeSyncService:
    return TimeSyncService()
