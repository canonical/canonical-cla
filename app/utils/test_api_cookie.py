import json
from unittest.mock import MagicMock

import pytest
from fastapi import Request, Response
from pydantic import BaseModel

from app.utils.api_cookie import APIKeyCookieModel, EncryptedAPIKeyCookie
from app.utils.crypto import AESCipher


class DummyModel(BaseModel):
    user_id: int
    name: str


class DummyCookieModel(APIKeyCookieModel[DummyModel]):
    @property
    def payload_model(self) -> type[DummyModel]:
        return DummyModel


@pytest.fixture
def secret_key():
    return "test-secret-key"


@pytest.fixture
def encrypted_cookie(secret_key):
    return EncryptedAPIKeyCookie(secret=secret_key, name="test_cookie")


@pytest.fixture
def model_cookie(secret_key):
    return DummyCookieModel(secret=secret_key, name="model_cookie")


@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.cookies = {}
    request.headers = {}
    return request


@pytest.mark.asyncio
async def test_encrypted_cookie_call_no_cookie(encrypted_cookie, mock_request):
    # Should return None if cookie is missing
    val = await encrypted_cookie(mock_request)
    assert val is None


@pytest.mark.asyncio
async def test_encrypted_cookie_call_valid_cookie(
    encrypted_cookie, mock_request, secret_key
):
    cipher = AESCipher(secret_key)
    data = {"foo": "bar"}
    encrypted_val = cipher.encrypt(json.dumps(data))

    mock_request.cookies = {"test_cookie": encrypted_val}

    val = await encrypted_cookie(mock_request)
    assert val == data


@pytest.mark.asyncio
async def test_encrypted_cookie_call_invalid_cookie_returns_none(
    encrypted_cookie, mock_request
):
    mock_request.cookies = {"test_cookie": "invalid-garbage"}
    val = await encrypted_cookie(mock_request)
    assert val is None


@pytest.mark.asyncio
async def test_encrypted_cookie_call_non_json_value(
    encrypted_cookie, mock_request, secret_key
):
    cipher = AESCipher(secret_key)
    # Encrypt a raw string not JSON
    raw_str = "simple_string"
    encrypted_val = cipher.encrypt(raw_str)

    mock_request.cookies = {"test_cookie": encrypted_val}

    val = await encrypted_cookie(mock_request)
    # It attempts to json load, if fails returns raw string
    assert val == raw_str


def test_encrypted_cookie_set_cookie(encrypted_cookie, secret_key):
    response = MagicMock(spec=Response)
    data = {"foo": "bar"}

    encrypted_cookie.set_cookie(response, value=data)

    response.set_cookie.assert_called_once()
    call_kwargs = response.set_cookie.call_args[1]
    assert call_kwargs["key"] == "test_cookie"

    # Verify we can decrypt the value passed to set_cookie
    encrypted_value = call_kwargs["value"]
    cipher = AESCipher(secret_key)
    decrypted = cipher.decrypt(encrypted_value)
    assert json.loads(decrypted or "") == data


@pytest.mark.asyncio
async def test_model_cookie_call_valid(model_cookie, mock_request, secret_key):
    cipher = AESCipher(secret_key)
    data = {"user_id": 123, "name": "Alice"}
    encrypted_val = cipher.encrypt(json.dumps(data))

    mock_request.cookies = {"model_cookie": encrypted_val}

    model = await model_cookie(mock_request)
    assert isinstance(model, DummyModel)
    assert model.user_id == 123
    assert model.name == "Alice"


@pytest.mark.asyncio
async def test_model_cookie_call_invalid_structure(
    model_cookie, mock_request, secret_key
):
    cipher = AESCipher(secret_key)
    data = {"user_id": "not-an-int", "name": "Alice"}  # user_id should be int
    encrypted_val = cipher.encrypt(json.dumps(data))

    mock_request.cookies = {"model_cookie": encrypted_val}

    # Should fail validation and return None
    model = await model_cookie(mock_request)
    assert model is None


@pytest.mark.asyncio
async def test_model_cookie_call_not_dict(model_cookie, mock_request, secret_key):
    cipher = AESCipher(secret_key)
    encrypted_val = cipher.encrypt("just a string")

    mock_request.cookies = {"model_cookie": encrypted_val}

    model = await model_cookie(mock_request)
    assert model is None


def test_model_cookie_set_cookie_model_instance(model_cookie, secret_key):
    response = MagicMock(spec=Response)
    model = DummyModel(user_id=456, name="Bob")

    model_cookie.set_cookie(response, value=model)

    response.set_cookie.assert_called_once()
    encrypted_value = response.set_cookie.call_args[1]["value"]

    cipher = AESCipher(secret_key)
    decrypted = cipher.decrypt(encrypted_value)
    assert json.loads(decrypted or "") == model.model_dump()
