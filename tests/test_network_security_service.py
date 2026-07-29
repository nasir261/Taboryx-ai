"""
Tests for outbound transport security validation.
"""

from src.services.network_security_service import NetworkSecurityService


class TestNetworkSecurityService:
    def test_rejects_non_https_urls(self):
        ok, message = NetworkSecurityService.validate_secure_url("http://example.com/api")
        assert not ok
        assert message == "Only HTTPS endpoints are allowed"

    def test_accepts_https_urls(self):
        ok, message = NetworkSecurityService.validate_secure_url("https://example.com/api")
        assert ok
        assert message == "URL is secure"

    def test_rejects_invalid_urls(self):
        ok, message = NetworkSecurityService.validate_secure_url("not-a-url")
        assert not ok
        assert message == "URL is invalid"
