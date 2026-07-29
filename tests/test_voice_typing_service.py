"""
Tests for voice typing service behavior.
"""

import tempfile
from pathlib import Path

from src.database.db import get_database, init_database
from src.services.app_settings_service import AppSettingsService
from src.services.voice_typing_service import VoiceTypingService


class _MemorySettingsService:
    def __init__(self):
        self.values = {}

    def get_setting(self, key, default=None):
        return self.values.get(key, default)

    def set_setting(self, key, value, encrypt=None):
        self.values[key] = value


class _FakeAudio:
    pass


class _FakeMicrophone:
    device_indices = []
    failing_indices = set()

    def __init__(self, device_index=None):
        self.device_index = device_index

    def __enter__(self):
        if self.device_index in _FakeMicrophone.failing_indices:
            raise OSError(f"Microphone {self.device_index} unavailable")
        _FakeMicrophone.device_indices.append(self.device_index)
        return "fake-source"

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    @staticmethod
    def list_microphone_names():
        return ["Windows Default Mic", "iPhone Mic Bridge"]


class _FakeRecognizer:
    def __init__(self, transcript="captured text", error=None):
        self.transcript = transcript
        self.error = error

    def adjust_for_ambient_noise(self, source, duration=0.3):
        return None

    def listen(self, source, timeout=5, phrase_time_limit=12):
        if self.error:
            raise self.error
        return _FakeAudio()

    def recognize_google(self, audio):
        return self.transcript


class _FakeSpeechModule:
    class WaitTimeoutError(Exception):
        pass

    class UnknownValueError(Exception):
        pass

    class RequestError(Exception):
        pass

    Microphone = _FakeMicrophone

    def __init__(self, recognizer=None):
        self._recognizer = recognizer or _FakeRecognizer()

    def Recognizer(self):
        return self._recognizer


def test_voice_typing_reports_missing_dependency():
    service = VoiceTypingService(speech_module=None, app_settings_service=_MemorySettingsService())
    service.import_error = "No module named 'speech_recognition'"
    service.reload_speech_module = lambda: None
    available, message = service.is_available()
    assert not available
    assert "speech recognition" in message.lower()


def test_voice_typing_captures_transcript():
    service = VoiceTypingService(speech_module=_FakeSpeechModule(), app_settings_service=_MemorySettingsService())
    success, message, text = service.capture_text()
    assert success
    assert message == "Voice typing captured text."
    assert text == "captured text"


def test_voice_typing_handles_timeout():
    recognizer = _FakeRecognizer(error=_FakeSpeechModule.WaitTimeoutError())
    service = VoiceTypingService(
        speech_module=_FakeSpeechModule(recognizer=recognizer),
        app_settings_service=_MemorySettingsService(),
    )
    success, message, text = service.capture_text()
    assert not success
    assert "timed out" in message.lower()
    assert text is None


class TestVoiceTypingService:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_voice_typing.db"
        init_database(self.db_path)
        _FakeMicrophone.device_indices = []
        _FakeMicrophone.failing_indices = set()

    def teardown_method(self):
        get_database().close()
        self.temp_dir.cleanup()

    def test_list_microphones_returns_detected_devices(self):
        service = VoiceTypingService(
            speech_module=_FakeSpeechModule(),
            app_settings_service=AppSettingsService(),
        )
        success, message, devices = service.list_microphones()
        assert success
        assert "Detected 2 microphone" in message
        assert devices[1]["name"] == "iPhone Mic Bridge"

    def test_microphone_diagnostics_include_runtime_details(self):
        service = VoiceTypingService(
            speech_module=_FakeSpeechModule(),
            app_settings_service=AppSettingsService(),
        )

        diagnostics = service.get_microphone_diagnostics()

        assert diagnostics["python_executable"]
        assert diagnostics["python_version"]
        assert diagnostics["speech_import_error"] is None

    def test_selected_microphone_is_persisted_and_used(self):
        service = VoiceTypingService(
            speech_module=_FakeSpeechModule(),
            app_settings_service=AppSettingsService(),
        )
        service.set_selected_microphone(1, "iPhone Mic Bridge")

        assert service.get_selected_microphone_index() == 1
        assert service.get_selected_microphone_name() == "iPhone Mic Bridge"

        success, _, text = service.capture_text()
        assert success
        assert text == "captured text"
        assert _FakeMicrophone.device_indices[-1] == 1

    def test_saved_microphone_name_is_used_when_device_order_changes(self):
        service = VoiceTypingService(
            speech_module=_FakeSpeechModule(),
            app_settings_service=AppSettingsService(),
        )
        service.set_selected_microphone(99, "iPhone Mic Bridge")

        resolved_index, resolved_name, warning = service.resolve_microphone_device()

        assert resolved_index == 1
        assert resolved_name == "iPhone Mic Bridge"
        assert "order changed" in warning.lower()

    def test_capture_text_falls_back_to_windows_default_when_saved_mic_fails(self):
        service = VoiceTypingService(
            speech_module=_FakeSpeechModule(),
            app_settings_service=AppSettingsService(),
        )
        service.set_selected_microphone(1, "iPhone Mic Bridge")
        _FakeMicrophone.failing_indices = {1}

        success, message, text = service.capture_text()

        assert success
        assert text == "captured text"
        assert "windows default microphone" in message.lower()
        assert _FakeMicrophone.device_indices[-1] is None

    def test_voice_typing_request_error_mentions_internet(self):
        class _RequestErrorRecognizer(_FakeRecognizer):
            def recognize_google(self, audio):
                raise _FakeSpeechModule.RequestError("network down")

        service = VoiceTypingService(
            speech_module=_FakeSpeechModule(recognizer=_RequestErrorRecognizer()),
            app_settings_service=_MemorySettingsService(),
        )

        success, message, text = service.capture_text()

        assert not success
        assert "internet connection" in message.lower()
        assert text is None
