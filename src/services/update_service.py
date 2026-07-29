"""
Update Service
Checks online for new MediStock AI versions, downloads and launches the installer.
"""

import json
import logging
import os
import subprocess
import tempfile
import threading
import urllib.request
from pathlib import Path
from typing import Callable, Optional, Tuple

from src.config import APP_VERSION, DATA_DIR

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Version manifest URL
# Point this to wherever you host medistock_version.json.
# The file must return JSON matching the schema shown in _parse_manifest().
# Default: a file inside the project that acts as a local stub so the
# feature works without a live server.  Replace with a real HTTPS URL
# once you have a hosting location.
# ------------------------------------------------------------------
UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/medistock-ai/releases/main/medistock_version.json"
UPDATE_MANIFEST_URL_FALLBACK = None   # optional second URL

DOWNLOAD_DIR = DATA_DIR / "updates"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _version_tuple(version_str: str) -> tuple:
    """Convert "1.2.3" → (1, 2, 3) for comparison."""
    try:
        return tuple(int(x) for x in str(version_str).strip().split("."))
    except Exception:
        return (0, 0, 0)


class UpdateService:
    """Checks for, downloads, and launches MediStock AI updates."""

    def __init__(self, manifest_url: Optional[str] = None):
        self.manifest_url = manifest_url or UPDATE_MANIFEST_URL
        self._latest_info: Optional[dict] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_current_version(self) -> str:
        return APP_VERSION

    def check_for_update(self, timeout: int = 8) -> Tuple[bool, Optional[dict], str]:
        """
        Check the remote manifest for a newer version.

        Returns:
            (update_available, manifest_dict, error_message)
        """
        try:
            manifest = self._fetch_manifest(timeout=timeout)
        except Exception as exc:
            msg = f"Could not reach update server: {exc}"
            logger.warning(msg)
            return False, None, msg

        if not manifest:
            return False, None, "Empty or invalid update manifest received."

        latest = manifest.get("version", "")
        if not latest:
            return False, None, "Update manifest is missing a version field."

        available = _version_tuple(latest) > _version_tuple(APP_VERSION)
        self._latest_info = manifest if available else None
        return available, manifest if available else None, ""

    def download_update(
        self,
        manifest: dict,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[bool, str, Optional[Path]]:
        """
        Download the installer listed in the manifest.

        Returns:
            (success, message, local_path_or_None)
        """
        url = manifest.get("download_url", "")
        filename = manifest.get("filename") or url.split("/")[-1] or "MediStockSetup.exe"
        if not url:
            return False, "Manifest has no download_url.", None

        dest = DOWNLOAD_DIR / filename
        try:
            self._download_file(url, dest, progress_callback)
        except Exception as exc:
            logger.error("Update download failed: %s", exc)
            return False, f"Download failed: {exc}", None

        return True, f"Downloaded to {dest}", dest

    def download_update_async(
        self,
        manifest: dict,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_complete: Optional[Callable[[bool, str, Optional[Path]], None]] = None,
    ):
        """Run download_update on a background thread so the UI stays responsive."""
        def _worker():
            result = self.download_update(manifest, progress_callback=on_progress)
            if on_complete:
                on_complete(*result)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def launch_installer(self, installer_path: Path) -> Tuple[bool, str]:
        """Launch the downloaded installer."""
        if not installer_path or not installer_path.exists():
            return False, f"Installer not found at {installer_path}"
        try:
            os.startfile(str(installer_path))
            return True, f"Installer launched: {installer_path.name}"
        except Exception as exc:
            logger.error("Failed to launch installer: %s", exc)
            return False, f"Could not launch installer: {exc}"

    def get_release_notes(self, manifest: dict) -> str:
        return manifest.get("release_notes") or "No release notes provided."

    def get_latest_cached(self) -> Optional[dict]:
        """Return the last fetched manifest if an update was found."""
        return self._latest_info

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fetch_manifest(self, timeout: int = 8) -> Optional[dict]:
        urls = [self.manifest_url]
        if UPDATE_MANIFEST_URL_FALLBACK:
            urls.append(UPDATE_MANIFEST_URL_FALLBACK)

        for url in urls:
            if not url:
                continue
            try:
                req = urllib.request.Request(url, headers={"User-Agent": f"MediStockAI/{APP_VERSION}"})
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    raw = response.read().decode("utf-8")
                    return json.loads(raw)
            except Exception as exc:
                logger.debug("Manifest fetch from %s failed: %s", url, exc)
        raise RuntimeError("All update manifest URLs failed.")

    def _download_file(
        self,
        url: str,
        dest: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        req = urllib.request.Request(url, headers={"User-Agent": f"MediStockAI/{APP_VERSION}"})
        with urllib.request.urlopen(req, timeout=60) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 65536
            with open(dest, "wb") as out_file:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total)
