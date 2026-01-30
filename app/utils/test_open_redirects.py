import pytest
from fastapi import HTTPException

from app.utils.open_redirects import (
    is_url_from_trusted_website,
    validate_open_redirect,
)


class TestValidateOpenRedirect:
    """Tests for validate_open_redirect."""

    def test_returns_true_for_localhost(self):
        assert validate_open_redirect("http://localhost/") is True
        assert validate_open_redirect("https://localhost/callback") is True

    def test_returns_true_for_localhost_with_port(self):
        assert validate_open_redirect("http://localhost:8000/path") is True
        assert validate_open_redirect("https://127.0.0.1:443/") is True

    def test_returns_true_for_trusted_wildcard_domains(self):
        assert validate_open_redirect("https://wiki.ubuntu.com/page") is True
        assert validate_open_redirect("https://api.canonical.com/v1") is True
        assert validate_open_redirect("https://foo.demos.haus/sign") is True

    def test_raises_for_untrusted_domain(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_open_redirect("https://evil.com/callback")
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid redirect URL"

        with pytest.raises(HTTPException):
            validate_open_redirect("https://ubuntu.com.evil.com/")

    def test_raises_for_empty_or_invalid_url(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_open_redirect("")
        assert exc_info.value.status_code == 400

        with pytest.raises(HTTPException):
            validate_open_redirect("not-a-url")


class TestIsUrlFromTrustedWebsite:
    """Tests for is_url_from_trusted_website using urlparse for domain extraction."""

    def test_domain_extraction_with_scheme_and_path(self):
        trusted = {"example.com"}
        assert is_url_from_trusted_website("https://example.com/path?q=1", trusted) is True
        assert is_url_from_trusted_website("http://example.com/", trusted) is True

    def test_domain_extraction_with_port(self):
        """urlparse is used so port is stripped from netloc (hostname)."""
        trusted = {"localhost", "example.com"}
        assert is_url_from_trusted_website("http://localhost:8000/callback", trusted) is True
        assert is_url_from_trusted_website("https://example.com:443/path", trusted) is True

    def test_domain_extraction_rejects_wrong_host(self):
        trusted = {"example.com"}
        assert is_url_from_trusted_website("https://other.com/path", trusted) is False

    def test_wildcard_pattern_matching(self):
        trusted = {"*.ubuntu.com", "ubuntu.com"}
        assert is_url_from_trusted_website("https://wiki.ubuntu.com/page", trusted) is True
        assert is_url_from_trusted_website("https://ubuntu.com/page", trusted) is True
        assert is_url_from_trusted_website("https://ubuntu.com.evil.com/", trusted) is False

    def test_empty_trusted_set(self):
        assert is_url_from_trusted_website("https://localhost/", set()) is False

    def test_no_netloc_returns_false(self):
        """URLs without a clear host (e.g. scheme-relative or malformed) are not trusted."""
        trusted = {"example.com"}
        assert is_url_from_trusted_website("/relative/path", trusted) is False


class TestIntegrationWithTrustedWebsites:
    """Integration tests using the app TRUSTED_WEBSITES constant."""

    def test_trusted_websites_allow_localhost_and_loopback(self):
        assert validate_open_redirect("http://localhost/") is True
        assert validate_open_redirect("http://127.0.0.1/") is True
        assert validate_open_redirect("http://0.0.0.0/") is True

    def test_trusted_websites_allow_canonical_and_ubuntu_wildcards(self):
        assert validate_open_redirect("https://login.ubuntu.com/") is True
        assert validate_open_redirect("https://api.canonical.com/") is True

    def test_trusted_websites_raise_for_untrusted(self):
        with pytest.raises(HTTPException):
            validate_open_redirect("https://evil.com/")
