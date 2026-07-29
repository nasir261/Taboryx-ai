"""
Tests for secure in-app web time synchronization.
"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.database.db import get_database, init_database
from src.services.time_sync_service import TimeSyncService


class TestTimeSyncService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_time_sync.db"
        init_database(self.db_path)

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_sync_time_updates_offset_and_now(self):
        target_utc = datetime.now(timezone.utc) + timedelta(seconds=120)
        service = TimeSyncService(fetch_utc_time=lambda: target_utc)
        service.set_enabled(True)

        success, message = service.sync_time()
        assert success
        assert message == "Time synchronized from secure web source"
        assert service.get_offset_seconds() == 0

        now_value = service.now()
        delta_seconds = (now_value - datetime.now()).total_seconds()
        assert abs(delta_seconds) < 2

    def test_sync_time_can_be_disabled(self):
        service = TimeSyncService(fetch_utc_time=lambda: datetime.now(timezone.utc))
        service.set_enabled(False)
        success, message = service.sync_time()
        assert not success
        assert message == "Time sync is disabled"

    def test_sync_time_handles_fetch_error(self):
        def _failing_fetch():
            raise ValueError("network down")

        service = TimeSyncService(fetch_utc_time=_failing_fetch)
        service.set_enabled(True)
        success, message = service.sync_time()
        assert not success
        assert message == "Time sync unavailable; using computer clock"

    def test_last_sync_value_available_after_success(self):
        target_utc = datetime.now(timezone.utc) + timedelta(seconds=30)
        service = TimeSyncService(fetch_utc_time=lambda: target_utc)
        service.set_enabled(True)

        success, _ = service.sync_time()
        assert success
        last_sync = service.get_last_sync_utc()
        assert last_sync is not None
        assert abs((datetime.now(timezone.utc) - last_sync).total_seconds()) < 5

    def test_sync_time_uses_last_sync_message_when_temporarily_unavailable(self):
        target_utc = datetime.now(timezone.utc) + timedelta(seconds=15)
        service = TimeSyncService(fetch_utc_time=lambda: target_utc)
        service.set_enabled(True)
        success, _ = service.sync_time()
        assert success

        service.fetch_utc_time = lambda: (_ for _ in ()).throw(OSError("forcibly closed by remote host"))
        success, message = service.sync_time()
        assert not success
        assert message == "Time sync temporarily unavailable; using computer clock"

    def test_parse_supported_time_api_formats(self):
        payload = {"dateTime": "2026-07-26T17:00:00+00:00"}
        parsed = TimeSyncService._parse_utc_datetime(payload)
        assert parsed.tzinfo is not None
        assert parsed.hour == 17

    def test_fetch_date_header_time_parses_utc_date_header(self, monkeypatch):
        class _FakeHeaders:
            def get(self, key):
                if key == "Date":
                    return "Sat, 26 Jul 2026 17:58:56 GMT"
                return None

        class _FakeResponse:
            headers = _FakeHeaders()

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def _fake_urlopen(*args, **kwargs):
            return _FakeResponse()

        monkeypatch.setattr("src.services.time_sync_service.urlopen", _fake_urlopen)
        parsed = TimeSyncService._fetch_date_header_time("https://www.google.com/generate_204")
        assert parsed.year == 2026
        assert parsed.minute == 58
