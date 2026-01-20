import pytest
from fastapi import HTTPException

from app.utils.base64 import Base64


def test_encode():
    assert Base64.encode("hello") == "aGVsbG8="


def test_decode():
    assert Base64.decode("aGVsbG8=") == "hello"


def test_decode_bytes():
    assert Base64.decode("aGVsbG8=", text=False) == b"hello"


def test_decode_invalid_base64():
    with pytest.raises(HTTPException) as exc_info:
        Base64.decode("invalid-base64-!!!")
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid base64 encoding"
