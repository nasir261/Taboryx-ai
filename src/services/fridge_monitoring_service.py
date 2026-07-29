"""
Fridge monitoring service for Wi-Fi-enabled pharmacy refrigeration devices.
"""

from datetime import datetime, timezone
import json
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.database.db import get_database


class FridgeMonitoringService:
    """Manage connected fridge devices and their temperature readings."""

    def __init__(self):
        self.db = get_database()

    def register_fridge(
        self,
        device_name: str,
        device_code: Optional[str] = None,
        location: Optional[str] = None,
        room_id: Optional[int] = None,
        connection_type: str = "wifi",
        endpoint_url: Optional[str] = None,
        min_temperature: Optional[float] = None,
        max_temperature: Optional[float] = None,
        notes: Optional[str] = None,
        is_active: bool = True,
    ) -> Tuple[bool, str, Optional[int]]:
        device_name = (device_name or "").strip()
        if not device_name:
            return False, "Device name is required", None

        device_code = (device_code or "").strip() or None
        if device_code and self._get_fridge_id_by_code(device_code) is not None:
            return False, "A fridge with that device code already exists", None

        payload = {
            "device_name": device_name,
            "device_code": device_code,
            "location": location.strip() if location else None,
            "room_id": room_id,
            "connection_type": (connection_type or "wifi").strip() or "wifi",
            "endpoint_url": endpoint_url.strip() if endpoint_url else None,
            "min_temperature": min_temperature,
            "max_temperature": max_temperature,
            "notes": notes.strip() if notes else None,
            "is_active": int(bool(is_active)),
        }

        fridge_id = self.db.insert("fridge_devices", payload)
        if not fridge_id:
            return False, "Failed to register fridge", None
        return True, "Fridge registered", fridge_id

    def get_fridge_by_id(self, fridge_id: int) -> Optional[Dict]:
        row = self.db.fetch_one(
            """
            SELECT fd.*, cr.room_name
            FROM fridge_devices fd
            LEFT JOIN clinical_rooms cr ON cr.id = fd.room_id
            WHERE fd.id = ?
            """,
            (fridge_id,),
        )
        if not row:
            return None
        return self._serialize_fridge(row)

    def get_fridges(self) -> List[Dict]:
        rows = self.db.fetch_all(
            """
            SELECT
                fd.*,
                cr.room_name,
                (
                    SELECT ftr.temperature_c
                    FROM fridge_temperature_readings ftr
                    WHERE ftr.fridge_device_id = fd.id
                    ORDER BY ftr.recorded_at DESC, ftr.id DESC
                    LIMIT 1
                ) AS latest_temperature_c,
                (
                    SELECT ftr.status
                    FROM fridge_temperature_readings ftr
                    WHERE ftr.fridge_device_id = fd.id
                    ORDER BY ftr.recorded_at DESC, ftr.id DESC
                    LIMIT 1
                ) AS latest_status,
                (
                    SELECT ftr.recorded_at
                    FROM fridge_temperature_readings ftr
                    WHERE ftr.fridge_device_id = fd.id
                    ORDER BY ftr.recorded_at DESC, ftr.id DESC
                    LIMIT 1
                ) AS latest_recorded_at
            FROM fridge_devices fd
            LEFT JOIN clinical_rooms cr ON cr.id = fd.room_id
            WHERE fd.is_active = 1
            ORDER BY fd.device_name
            """
        )
        return [self._serialize_fridge(row) for row in rows]

    def get_readings(self, fridge_id: Optional[int] = None, limit: int = 12) -> List[Dict]:
        if fridge_id is not None:
            rows = self.db.fetch_all(
                """
                SELECT ftr.*, fd.device_name
                FROM fridge_temperature_readings ftr
                JOIN fridge_devices fd ON fd.id = ftr.fridge_device_id
                WHERE ftr.fridge_device_id = ?
                ORDER BY ftr.recorded_at DESC, ftr.id DESC
                LIMIT ?
                """,
                (fridge_id, limit),
            )
        else:
            rows = self.db.fetch_all(
                """
                SELECT ftr.*, fd.device_name
                FROM fridge_temperature_readings ftr
                JOIN fridge_devices fd ON fd.id = ftr.fridge_device_id
                ORDER BY ftr.recorded_at DESC, ftr.id DESC
                LIMIT ?
                """,
                (limit,),
            )
        return [self._serialize_reading(row) for row in rows]

    def record_temperature(
        self,
        fridge_id: Optional[int] = None,
        device_code: Optional[str] = None,
        temperature_c: Optional[float] = None,
        source: str = "wifi",
        notes: Optional[str] = None,
        recorded_at: Optional[datetime] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        fridge = None
        if fridge_id is not None:
            fridge = self.get_fridge_by_id(fridge_id)
        elif device_code:
            fridge_id_from_code = self._get_fridge_id_by_code(device_code)
            if fridge_id_from_code is not None:
                fridge = self.get_fridge_by_id(fridge_id_from_code)
                fridge_id = fridge_id_from_code

        if not fridge:
            return False, "Fridge not found", None

        try:
            temperature_value = float(temperature_c)
        except (TypeError, ValueError):
            return False, "temperature_c must be a numeric value", None

        status = self._evaluate_status(temperature_value, fridge.get("min_temperature"), fridge.get("max_temperature"))
        timestamp = recorded_at or datetime.now(timezone.utc)
        payload = {
            "fridge_device_id": fridge_id,
            "temperature_c": round(temperature_value, 1),
            "status": status,
            "source": (source or "wifi").strip() or "wifi",
            "notes": notes.strip() if notes else None,
            "recorded_at": timestamp,
        }
        reading_id = self.db.insert("fridge_temperature_readings", payload)
        if not reading_id:
            return False, "Failed to save temperature reading", None
        return True, "Temperature reading recorded", reading_id

    def check_wifi_connection(self, fridge_id: int, timeout_seconds: int = 5) -> Tuple[bool, str, Optional[Dict]]:
        fridge = self.get_fridge_by_id(fridge_id)
        if not fridge:
            return False, "Fridge not found", None

        endpoint_url = (fridge.get("endpoint_url") or "").strip()
        if not endpoint_url:
            return False, "This fridge does not have an endpoint URL configured", None

        request = Request(endpoint_url, method="GET")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                status_code = int(getattr(response, "status", 200) or 200)
                content_type = (response.headers.get("Content-Type") or "").lower()
                payload_text = response.read().decode("utf-8")
        except HTTPError as exc:
            return False, f"Wi-Fi endpoint returned HTTP {exc.code}", None
        except URLError as exc:
            reason = str(exc.reason) if exc.reason else str(exc)
            return False, f"Unable to reach Wi-Fi endpoint: {reason}", None
        except TimeoutError:
            return False, "Wi-Fi endpoint timed out", None

        preview_payload = None
        if "application/json" in content_type and payload_text:
            try:
                preview_payload = json.loads(payload_text)
            except json.JSONDecodeError:
                preview_payload = {"raw": payload_text[:200]}
        elif payload_text:
            preview_payload = {"raw": payload_text[:200]}

        return True, f"Connected to Wi-Fi endpoint (HTTP {status_code})", preview_payload

    def pull_temperature_from_wifi_endpoint(self, fridge_id: int, timeout_seconds: int = 5) -> Tuple[bool, str, Optional[int]]:
        fridge = self.get_fridge_by_id(fridge_id)
        if not fridge:
            return False, "Fridge not found", None

        endpoint_url = (fridge.get("endpoint_url") or "").strip()
        if not endpoint_url:
            return False, "This fridge does not have an endpoint URL configured", None

        request = Request(endpoint_url, method="GET")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                payload_text = response.read().decode("utf-8")
        except HTTPError as exc:
            return False, f"Wi-Fi endpoint returned HTTP {exc.code}", None
        except URLError as exc:
            reason = str(exc.reason) if exc.reason else str(exc)
            return False, f"Unable to reach Wi-Fi endpoint: {reason}", None
        except TimeoutError:
            return False, "Wi-Fi endpoint timed out", None

        if not payload_text.strip():
            return False, "Wi-Fi endpoint returned an empty response", None

        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError:
            return False, "Wi-Fi endpoint did not return valid JSON", None

        temperature_c = self._extract_temperature(payload)
        if temperature_c is None:
            return False, "Wi-Fi endpoint JSON must include a numeric temperature field", None

        return self.record_temperature(
            fridge_id=fridge_id,
            temperature_c=temperature_c,
            source="wifi",
            notes="Recorded from Wi-Fi endpoint",
        )

    def _get_fridge_id_by_code(self, device_code: str) -> Optional[int]:
        row = self.db.fetch_one(
            "SELECT id FROM fridge_devices WHERE device_code = ? LIMIT 1",
            (device_code.strip(),),
        )
        return row.get("id") if row else None

    def _serialize_fridge(self, row: Dict) -> Dict:
        latest_temperature = row.get("latest_temperature_c")
        if latest_temperature is not None:
            latest_temperature = round(float(latest_temperature), 1)
        return {
            "id": row.get("id"),
            "device_name": row.get("device_name"),
            "device_code": row.get("device_code"),
            "location": row.get("location"),
            "room_id": row.get("room_id"),
            "room_name": row.get("room_name"),
            "connection_type": row.get("connection_type"),
            "endpoint_url": row.get("endpoint_url"),
            "min_temperature": row.get("min_temperature"),
            "max_temperature": row.get("max_temperature"),
            "notes": row.get("notes"),
            "is_active": bool(row.get("is_active", 0)),
            "latest_temperature_c": latest_temperature,
            "latest_status": row.get("latest_status"),
            "latest_recorded_at": row.get("latest_recorded_at"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

    def _serialize_reading(self, row: Dict) -> Dict:
        temperature = row.get("temperature_c")
        if temperature is not None:
            temperature = round(float(temperature), 1)
        return {
            "id": row.get("id"),
            "fridge_device_id": row.get("fridge_device_id"),
            "device_name": row.get("device_name"),
            "temperature_c": temperature,
            "status": row.get("status"),
            "source": row.get("source"),
            "notes": row.get("notes"),
            "recorded_at": row.get("recorded_at"),
            "created_at": row.get("created_at"),
        }

    def _evaluate_status(self, temperature_c: float, min_temperature, max_temperature) -> str:
        if min_temperature is not None and temperature_c < float(min_temperature):
            return "alert"
        if max_temperature is not None and temperature_c > float(max_temperature):
            return "alert"
        return "normal"

    def _extract_temperature(self, payload: Dict) -> Optional[float]:
        if not isinstance(payload, dict):
            return None
        candidates = (
            payload.get("temperature_c"),
            payload.get("temperature"),
            payload.get("temp_c"),
            payload.get("temp"),
            payload.get("value"),
        )
        for candidate in candidates:
            if candidate is None:
                continue
            try:
                return float(candidate)
            except (TypeError, ValueError):
                continue
        return None
