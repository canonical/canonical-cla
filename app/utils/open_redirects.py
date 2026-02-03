from urllib.parse import urlparse

from fastapi import HTTPException

from app.utils.trusted_websites import TRUSTED_WEBSITES


def validate_open_redirect(url: str) -> bool:
    """
    Validates that a redirect URL is safe by ensuring its host is in the trusted websites list.
    Returns True if the URL is safe to redirect to, False otherwise.
    """
    if not is_url_from_trusted_website(url, TRUSTED_WEBSITES):
        raise HTTPException(status_code=400, detail="Invalid redirect URL")
    return True


def _get_domain_from_url(url: str) -> str | None:
    """Extract the hostname (domain without port) from a URL using urlparse."""
    parsed = urlparse(url)
    # hostname is None when scheme is missing and netloc is empty (e.g. "example.com/path")
    if parsed.hostname is not None:
        return parsed.hostname
    if parsed.netloc:
        return parsed.netloc.split(":")[0]
    return None


def is_url_from_trusted_website(url, trusted_websites: set[str]):
    """
    Validates if the URL is a match for the trusted websites.
    The trusted websites are a set of strings that are used to validate the URL.
    """
    domain = _get_domain_from_url(url)
    if domain is None:
        return False

    for pattern in trusted_websites:
        if pattern.startswith("*"):
            if domain.endswith(pattern[1:]):
                return True
        elif domain == pattern:
            return True
    return False
