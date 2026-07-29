"""
Tests for session timeout service.
"""

from datetime import datetime, timedelta

from src.services.session_timeout_service import SessionTimeoutService


class TestSessionTimeoutService:
    def test_seconds_remaining_decreases_with_time(self):
        service = SessionTimeoutService(timeout_minutes=1)
        start = datetime(2026, 1, 1, 12, 0, 0)
        service.record_activity(start)

        remaining = service.get_seconds_remaining(start + timedelta(seconds=20))
        assert remaining == 40

    def test_record_activity_resets_timeout(self):
        service = SessionTimeoutService(timeout_minutes=1)
        start = datetime(2026, 1, 1, 12, 0, 0)
        service.record_activity(start)
        service.record_activity(start + timedelta(seconds=30))

        remaining = service.get_seconds_remaining(start + timedelta(seconds=50))
        assert remaining == 40

    def test_is_expired_when_timeout_reached(self):
        service = SessionTimeoutService(timeout_minutes=1)
        start = datetime(2026, 1, 1, 12, 0, 0)
        service.record_activity(start)

        assert not service.is_expired(start + timedelta(seconds=59))
        assert service.is_expired(start + timedelta(seconds=60))

    def test_warning_threshold_detection(self):
        service = SessionTimeoutService(timeout_minutes=1)
        start = datetime(2026, 1, 1, 12, 0, 0)
        service.record_activity(start)

        assert not service.is_warning_threshold_reached(20, start + timedelta(seconds=39))
        assert service.is_warning_threshold_reached(20, start + timedelta(seconds=40))

    def test_warning_threshold_must_be_positive(self):
        service = SessionTimeoutService(timeout_minutes=1)

        try:
            service.is_warning_threshold_reached(0)
            assert False, "Expected ValueError"
        except ValueError:
            pass
