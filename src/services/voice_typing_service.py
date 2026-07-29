"""
Voice typing service.
Provides microphone-based dictation for text-entry fields.
"""

import importlib
import logging
import sys
from typing import List, Optional, Tuple

from src.services.app_settings_service import AppSettingsService

logger = logging.getLogger(__name__)
_AUTO_LOAD = object()


def _load_speech_recognition():
    try:
        return importlib.import_module("speech_recognition"), None
    except ImportError as e:
        return None, str(e)


class VoiceTypingService:
    """Capture dictated text from the system microphone."""

    SELECTED_MICROPHONE_INDEX_KEY = "voice_typing.selected_microphone_index"
    SELECTED_MICROPHONE_NAME_KEY = "voice_typing.selected_microphone_name"

    def __init__(self, speech_module=_AUTO_LOAD, app_settings_service: Optional[AppSettingsService] = None):
        self.speech_module = None
        self.import_error: Optional[str] = None
        if speech_module is _AUTO_LOAD:
            self.reload_speech_module()
        else:
            self.speech_module = speech_module
        self.app_settings_service = app_settings_service or AppSettingsService()

    def reload_speech_module(self):
        self.speech_module, self.import_error = _load_speech_recognition()
        if self.import_error:
            logger.warning(f"Speech recognition import unavailable: {self.import_error}")
        return self.speech_module

    def get_runtime_details(self) -> dict:
        return {
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
            "speech_import_error": self.import_error,
        }

    def is_available(self) -> Tuple[bool, str]:
        if self.speech_module is None:
            self.reload_speech_module()
        if self.speech_module is None:
            if self.import_error:
                return False, f"Voice typing is unavailable because speech recognition failed to load: {self.import_error}"
            return False, "Voice typing is unavailable because SpeechRecognition is not installed."
        if not hasattr(self.speech_module, "Microphone"):
            return False, "Voice typing is unavailable because microphone support is missing."
        return True, "Voice typing is available."

    def list_microphones(self) -> Tuple[bool, str, List[dict]]:
        available, message = self.is_available()
        if not available:
            return False, message, []

        microphone_class = getattr(self.speech_module, "Microphone", None)
        if microphone_class is None or not hasattr(microphone_class, "list_microphone_names"):
            return False, "Microphone enumeration is unavailable on this system.", []

        try:
            names = microphone_class.list_microphone_names()
        except Exception as e:
            logger.error(f"Error listing microphones: {e}")
            return False, f"Could not list microphones: {str(e)}", []

        devices = [{"index": index, "name": name} for index, name in enumerate(names)]
        if not devices:
            return False, "No microphones were detected by Windows.", []
        return True, f"Detected {len(devices)} microphone(s).", devices

    @staticmethod
    def _normalize_microphone_name(name: Optional[str]) -> str:
        return " ".join((name or "").strip().lower().split())

    def _find_microphone_name(self, devices: List[dict], device_index: Optional[int]) -> Optional[str]:
        if device_index is None:
            return None
        match = next((device["name"] for device in devices if device["index"] == device_index), None)
        return match

    def resolve_microphone_device(
        self,
        device_index: Optional[int] = None,
        device_name: Optional[str] = None,
    ) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        success, _, devices = self.list_microphones()
        if not success:
            return device_index, device_name, None

        resolved_index = self.get_selected_microphone_index() if device_index is None else device_index
        resolved_name = self.get_selected_microphone_name() if device_name is None else device_name
        normalized_name = self._normalize_microphone_name(resolved_name)

        if resolved_index is None and not normalized_name:
            return None, None, None

        current_name = self._find_microphone_name(devices, resolved_index)
        if current_name and (not normalized_name or self._normalize_microphone_name(current_name) == normalized_name):
            return resolved_index, current_name, None

        if normalized_name:
            name_match = next(
                (device for device in devices if self._normalize_microphone_name(device["name"]) == normalized_name),
                None,
            )
            if name_match:
                warning = "Saved microphone order changed; using the matching device name."
                return name_match["index"], name_match["name"], warning

        warning = "Saved microphone is unavailable; using the Windows default microphone."
        return None, None, warning

    def get_selected_microphone_index(self) -> Optional[int]:
        raw = self.app_settings_service.get_setting(self.SELECTED_MICROPHONE_INDEX_KEY, "")
        if raw in (None, ""):
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def get_selected_microphone_name(self) -> Optional[str]:
        selected_index = self.get_selected_microphone_index()
        selected_name = self.app_settings_service.get_setting(self.SELECTED_MICROPHONE_NAME_KEY, "")
        if selected_name:
            return selected_name

        success, _, devices = self.list_microphones()
        if not success or selected_index is None:
            return None
        match = next((device["name"] for device in devices if device["index"] == selected_index), None)
        return match

    def set_selected_microphone(self, device_index: Optional[int], device_name: Optional[str] = None):
        if device_index is None:
            self.app_settings_service.set_setting(self.SELECTED_MICROPHONE_INDEX_KEY, "")
            self.app_settings_service.set_setting(self.SELECTED_MICROPHONE_NAME_KEY, "")
            return

        self.app_settings_service.set_setting(self.SELECTED_MICROPHONE_INDEX_KEY, str(device_index))
        resolved_name = device_name
        if not resolved_name:
            success, _, devices = self.list_microphones()
            if success:
                match = next((device["name"] for device in devices if device["index"] == device_index), None)
                resolved_name = match or ""
        self.app_settings_service.set_setting(self.SELECTED_MICROPHONE_NAME_KEY, resolved_name or "")

    def get_microphone_diagnostics(self) -> dict:
        available, availability_message = self.is_available()
        devices_success, devices_message, devices = self.list_microphones()
        selected_index = self.get_selected_microphone_index()
        selected_name = self.get_selected_microphone_name()
        runtime_details = self.get_runtime_details()
        return {
            "available": available,
            "availability_message": availability_message,
            "devices_available": devices_success,
            "devices_message": devices_message,
            "devices": devices,
            "selected_index": selected_index,
            "selected_name": selected_name,
            "python_executable": runtime_details["python_executable"],
            "python_version": runtime_details["python_version"],
            "speech_import_error": runtime_details["speech_import_error"],
        }

    def capture_text(
        self,
        timeout: int = 8,
        phrase_time_limit: int = 15,
        device_index: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        available, message = self.is_available()
        if not available:
            return False, message, None

        recognizer = self.speech_module.Recognizer()
        selected_name = None if device_index is not None else self.get_selected_microphone_name()
        selected_index, selected_name, selection_warning = self.resolve_microphone_device(
            device_index=device_index,
            device_name=selected_name,
        )
        try:
            with self.speech_module.Microphone(device_index=selected_index) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except self.speech_module.WaitTimeoutError:
            return False, "Voice typing timed out while waiting for speech.", None
        except Exception as e:
            if selected_index is not None:
                logger.warning(f"Saved microphone failed for voice typing, retrying Windows default: {e}")
                try:
                    with self.speech_module.Microphone(device_index=None) as source:
                        recognizer.adjust_for_ambient_noise(source, duration=0.3)
                        audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                    selection_warning = "Selected microphone was unavailable; used the Windows default microphone."
                except self.speech_module.WaitTimeoutError:
                    return False, "Voice typing timed out while waiting for speech.", None
                except Exception as fallback_error:
                    logger.error(f"Error accessing fallback microphone for voice typing: {fallback_error}")
                    return False, f"Voice typing could not access the microphone: {str(fallback_error)}", None
            else:
                logger.error(f"Error accessing microphone for voice typing: {e}")
                return False, f"Voice typing could not access the microphone: {str(e)}", None

        try:
            text = recognizer.recognize_google(audio).strip()
            if not text:
                return False, "Voice typing did not detect any speech.", None
            success_message = (
                f"{selection_warning} Voice typing captured text."
                if selection_warning
                else "Voice typing captured text."
            )
            return True, success_message, text
        except self.speech_module.UnknownValueError:
            return False, "Voice typing could not understand the speech.", None
        except self.speech_module.RequestError as e:
            logger.error(f"Voice typing recognition request failed: {e}")
            return False, "Voice typing recognition failed. Check the internet connection and try again.", None
        except Exception as e:
            logger.error(f"Unexpected voice typing failure: {e}")
            return False, f"Voice typing failed: {str(e)}", None


_voice_typing_service: Optional[VoiceTypingService] = None


def get_voice_typing_service() -> VoiceTypingService:
    global _voice_typing_service
    if _voice_typing_service is None:
        _voice_typing_service = VoiceTypingService()
    return _voice_typing_service
