import pytest
from fastapi import Request, Response

from app.utils import EncryptedAPIKeyCookie


@pytest.fixture
def secret():
    return "super-secret"


@pytest.fixture
def cookie(secret):
    return EncryptedAPIKeyCookie(secret=secret, name="test-cookie")


@pytest.fixture
def response():
    return Response()


@pytest.mark.asyncio
async def test_encrypted_api_key_cookie_set_and_encrypt(cookie, response):
    """Test that the cookie is set in the response and the value is encrypted."""
    cookie.set_cookie(response, value="test-value")

    cookie_header_value = next(
        value.decode("utf-8")
        for header, value in response.raw_headers
        if header == b"set-cookie"
    )

    assert cookie_header_value is not None
    assert "test-value" not in cookie_header_value  # Ensure the value is encrypted


@pytest.mark.asyncio
async def test_encrypted_api_key_cookie_decrypt(cookie):
    """Test that the cookie can be decrypted when provided with the correct secret."""
    response = Response()
    cookie.set_cookie(response, value="test-value")

    cookie_header_value = next(
        value.decode("utf-8")
        for header, value in response.raw_headers
        if header == b"set-cookie"
    )

    request = Request(
        scope={
            "type": "http",
            "method": "GET",
            "headers": [(b"cookie", cookie_header_value.encode("utf-8"))],
        }
    )

    decrypted_value = await cookie(request)
    assert decrypted_value.startswith("test-value")


@pytest.mark.asyncio
async def test_encrypted_api_key_cookie_modified_value(cookie):
    """Test that the cookie cannot be decrypted when its value is modified."""
    request = Request(
        scope={
            "type": "http",
            "method": "GET",
            "headers": [
                (b"cookie", b'test-cookie="modified-value"; Path=/; SameSite=lax')
            ],
        }
    )

    decrypted_value = await cookie(request)
    assert decrypted_value is None


@pytest.mark.asyncio
async def test_encrypted_api_key_cookie_empty_value(cookie):
    """Test that the cookie returns None when its value is empty."""
    request = Request(
        scope={
            "type": "http",
            "method": "GET",
            "headers": [(b"cookie", b'test-cookie=""; Path=/; SameSite=lax')],
        }
    )

    decrypted_value = await cookie(request)
    assert decrypted_value is None
