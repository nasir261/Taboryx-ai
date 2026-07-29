"""
Wi-Fi connection service for admin-managed Windows network access.
"""

import ctypes
import logging
import os
import re
import subprocess
import tempfile
import xml.sax.saxutils as saxutils
from pathlib import Path
from typing import List, Optional, Tuple

from src.services.app_settings_service import AppSettingsService

logger = logging.getLogger(__name__)


class WiFiConnectionService:
    """Manage local Wi-Fi scanning and connection from the desktop app."""

    def __init__(self, app_settings_service: Optional[AppSettingsService] = None):
        self.app_settings_service = app_settings_service or AppSettingsService()

    @staticmethod
    def is_windows_admin() -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def scan_available_networks(self) -> List[dict]:
        """Return nearby Wi-Fi SSIDs, forcing Windows to refresh its scan cache."""
        import time
        try:
            # First call wakes the Windows WLAN service scan cache
            subprocess.run(
                ["netsh", "wlan", "show", "networks"],
                capture_output=True, text=True, check=False,
            )
            # Wait briefly so Windows can collect fresh beacon frames
            time.sleep(2)

            # Second call with mode=Bssid gives full per-AP detail
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=Bssid"],
                capture_output=True, text=True, check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "netsh failed")

            networks = self._parse_show_networks_output(result.stdout)

            # Mark the currently connected network so the UI can highlight it
            try:
                connected = self.get_connected_network()
            except Exception:
                connected = None
            for net in networks:
                net["connected"] = (connected and net["ssid"] == connected)

            return networks
        except Exception as exc:
            logger.error("Unable to scan Wi-Fi networks: %s", exc)
            raise RuntimeError(str(exc)) from exc

    def get_connected_network(self) -> Optional[str]:
        """Return the currently connected Wi-Fi SSID, if any."""
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "netsh failed")
            for line in result.stdout.splitlines():
                if line.strip().lower().startswith("ssid"):
                    value = line.split(":", 1)[1].strip()
                    if value:
                        return value
            return None
        except Exception as exc:
            logger.error("Unable to determine current Wi-Fi network: %s", exc)
            raise RuntimeError(str(exc)) from exc

    def save_network_credentials(self, ssid: str, username: str, password: str) -> None:
        normalized = self._normalize_key(ssid)
        self.app_settings_service.set_setting(f"wifi.{normalized}.ssid", ssid)
        if username:
            self.app_settings_service.set_setting(f"wifi.{normalized}.username", username)
        else:
            self.app_settings_service.set_setting(f"wifi.{normalized}.username", "")
        self.app_settings_service.set_setting(f"wifi.{normalized}.password", password, encrypt=True)
        self.app_settings_service.set_setting("wifi.last_ssid", ssid)

    def get_saved_network_credentials(self, ssid: str) -> Tuple[str, str]:
        normalized = self._normalize_key(ssid)
        username = self.app_settings_service.get_setting(f"wifi.{normalized}.username", "") or ""
        password = self.app_settings_service.get_setting(f"wifi.{normalized}.password", "") or ""
        return username, password

    def connect_to_network(self, ssid: str, password: str, username: str = "") -> Tuple[bool, str]:
        if not ssid:
            return False, "A Wi-Fi SSID is required"
        if not password:
            return False, "A Wi-Fi password is required"
        if not self.is_windows_admin():
            return False, "Administrator privileges are required to manage Wi-Fi connections"

        try:
            self.save_network_credentials(ssid, username, password)
            profile_path = self._write_profile_file(ssid, password)
            try:
                self._delete_profile(ssid)
                self._add_profile(profile_path)
                self._connect_to_profile(ssid)
                return True, f"Connected to {ssid}"
            finally:
                try:
                    os.unlink(profile_path)
                except OSError:
                    pass
        except Exception as exc:
            logger.error("Unable to connect to Wi-Fi network %s: %s", ssid, exc)
            return False, str(exc)

    def _parse_show_networks_output(self, output: str) -> List[dict]:
        """Parse netsh wlan show networks output into a list of network dicts."""
        networks = []
        current: dict = {}
        for line in output.splitlines():
            stripped = line.strip()

            # Match SSID lines — "SSID 1 : MyNetwork" or "SSID 1 : "
            ssid_match = re.match(r"^SSID\s+\d+\s*:\s*(.*)$", stripped)
            if ssid_match:
                if current.get("ssid"):
                    networks.append(current)
                current = {"ssid": ssid_match.group(1).strip(), "signal": "", "auth": ""}
                continue

            # Signal strength
            sig_match = re.match(r"^Signal\s*:\s*(\d+%?)$", stripped, re.IGNORECASE)
            if sig_match and current:
                current["signal"] = sig_match.group(1)
                continue

            # Authentication type
            auth_match = re.match(r"^Authentication\s*:\s*(.+)$", stripped, re.IGNORECASE)
            if auth_match and current:
                current["auth"] = auth_match.group(1).strip()

        if current.get("ssid"):
            networks.append(current)

        # Deduplicate by SSID, keeping the entry with the highest signal
        seen: dict = {}
        for net in networks:
            ssid = net["ssid"]
            if not ssid:
                continue
            if ssid not in seen:
                seen[ssid] = net
            else:
                # Keep whichever has higher signal
                existing_sig = int(re.sub(r"\D", "", seen[ssid].get("signal", "0") or "0") or 0)
                new_sig = int(re.sub(r"\D", "", net.get("signal", "0") or "0") or 0)
                if new_sig > existing_sig:
                    seen[ssid] = net

        return sorted(seen.values(), key=lambda n: int(re.sub(r"\D", "", n.get("signal", "0") or "0") or 0), reverse=True)

    def _write_profile_file(self, ssid: str, password: str) -> str:
        profile_xml = f"""<?xml version=\"1.0\"?>
<WLANProfile xmlns=\"http://www.microsoft.com/networking/WLAN/profile/v1\">
  <name>{saxutils.escape(ssid)}</name>
  <SSIDConfig>
    <SSID>
      <name>{saxutils.escape(ssid)}</name>
    </SSID>
  </SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>auto</connectionMode>
  <MSM>
    <security>
      <authEncryption>
        <authentication>WPA2PSK</authentication>
        <encryption>AES</encryption>
        <useOneX>false</useOneX>
      </authEncryption>
      <sharedKey>
        <keyType>passPhrase</keyType>
        <protected>false</protected>
        <keyMaterial>{saxutils.escape(password)}</keyMaterial>
      </sharedKey>
    </security>
  </MSM>
</WLANProfile>"""
        temp_handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".xml", delete=False)
        try:
            temp_handle.write(profile_xml)
            temp_handle.flush()
            return temp_handle.name
        finally:
            temp_handle.close()

    def _delete_profile(self, ssid: str) -> None:
        subprocess.run(["netsh", "wlan", "delete", "profile", f"name={ssid}"], capture_output=True, text=True, check=False)

    def _add_profile(self, profile_path: str) -> None:
        result = subprocess.run(["netsh", "wlan", "add", "profile", f"filename={profile_path}", "user=all"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Unable to add Wi-Fi profile")

    def _connect_to_profile(self, ssid: str) -> None:
        result = subprocess.run(["netsh", "wlan", "connect", f"name={ssid}"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Unable to connect to Wi-Fi profile")

    @staticmethod
    def _normalize_key(value: str) -> str:
        cleaned = (value or "").strip().lower()
        return re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_") or "default"
