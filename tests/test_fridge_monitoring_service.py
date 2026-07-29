"""Tests for fridge monitoring service."""

import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from src.database.db import get_database, init_database
from src.services.fridge_monitoring_service import FridgeMonitoringService


class TestFridgeMonitoringService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_fridge_monitoring.db"
        init_database(self.db_path)
        self.service = FridgeMonitoringService()

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_register_fridge_and_record_temperature(self):
        success, message, fridge_id = self.service.register_fridge(
            device_name="Pharmacy fridge A",
            device_code="FR-001",
            location="Pharmacy store room",
            min_temperature=2.0,
            max_temperature=8.0,
        )
        assert success
        assert fridge_id is not None

        fridges = self.service.get_fridges()
        assert len(fridges) == 1
        assert fridges[0]["device_name"] == "Pharmacy fridge A"

        success, message, reading_id = self.service.record_temperature(
            device_code="FR-001",
            temperature_c=3.2,
            notes="Door opened",
        )
        assert success
        assert reading_id is not None

        fridges = self.service.get_fridges()
        assert fridges[0]["latest_temperature_c"] == 3.2
        assert fridges[0]["latest_status"] == "normal"

        readings = self.service.get_readings(fridge_id=fridge_id, limit=5)
        assert len(readings) == 1
        assert readings[0]["temperature_c"] == 3.2
        assert readings[0]["status"] == "normal"

    def test_out_of_range_temperature_is_flagged(self):
        success, _, fridge_id = self.service.register_fridge(
            device_name="Pharmacy fridge B",
            device_code="FR-002",
            min_temperature=2.0,
            max_temperature=8.0,
        )
        assert success

        success, _, _ = self.service.record_temperature(
            fridge_id=fridge_id,
            temperature_c=10.5,
        )
        assert success

        fridges = self.service.get_fridges()
        assert fridges[0]["latest_status"] == "alert"

    def test_wifi_connection_and_sync_from_endpoint(self):
        success, _, fridge_id = self.service.register_fridge(
            device_name="Pharmacy fridge C",
            device_code="FR-003",
            endpoint_url="http://192.168.0.88:9000/temperature",
            min_temperature=2.0,
            max_temperature=8.0,
        )
        assert success
        assert fridge_id is not None

        class _FakeResponse:
            status = 200

            def __init__(self, payload):
                self._payload = payload
                self.headers = {"Content-Type": "application/json"}

            def read(self):
                return self._payload.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch("src.services.fridge_monitoring_service.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(json.dumps({"temperature_c": 4.8}))
            ok, message, preview = self.service.check_wifi_connection(fridge_id=fridge_id)
            assert ok
            assert "Connected to Wi-Fi endpoint" in message
            assert preview["temperature_c"] == 4.8

        with patch("src.services.fridge_monitoring_service.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(json.dumps({"temperature": 5.3}))
            ok, message, reading_id = self.service.pull_temperature_from_wifi_endpoint(fridge_id=fridge_id)
            assert ok
            assert reading_id is not None

        readings = self.service.get_readings(fridge_id=fridge_id, limit=1)
        assert readings[0]["temperature_c"] == 5.3
        assert readings[0]["source"] == "wifi"

    def test_wifi_sync_requires_temperature_field(self):
        success, _, fridge_id = self.service.register_fridge(
            device_name="Pharmacy fridge D",
            endpoint_url="http://192.168.0.99:9000/status",
        )
        assert success
        assert fridge_id is not None

        class _FakeResponse:
            status = 200

            def __init__(self, payload):
                self._payload = payload
                self.headers = {"Content-Type": "application/json"}

            def read(self):
                return self._payload.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch("src.services.fridge_monitoring_service.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(json.dumps({"status": "ok"}))
            ok, message, reading_id = self.service.pull_temperature_from_wifi_endpoint(fridge_id=fridge_id)
            assert not ok
            assert reading_id is None
            assert "temperature field" in message
