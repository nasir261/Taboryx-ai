"""
Network security guardrails.
"""

from urllib.parse import urlparse

from src.config import ENFORCE_HTTPS_ONLY


class NetworkSecurityService:
    """Validates outbound URLs against transport security policy."""

    @staticmethod
    def validate_secure_url(url: str):
        parsed = urlparse((url or "").strip())
        if not parsed.scheme or not parsed.netloc:
            return False, "URL is invalid"
        if ENFORCE_HTTPS_ONLY and parsed.scheme.lower() != "https":
            return False, "Only HTTPS endpoints are allowed"
        return True, "URL is secure"
