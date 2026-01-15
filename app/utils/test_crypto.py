import base64
from unittest.mock import patch

import pytest

from app.utils.crypto import AESCipher, cipher


@pytest.fixture
def secret_key():
    return "secret-key-must-be-very-long-to-be-secure"


@pytest.fixture
def aes_cipher(secret_key):
    return AESCipher(secret_key)


def test_encrypt_decrypt(aes_cipher):
    original_text = "test-message"
    encrypted = aes_cipher.encrypt(original_text)
    assert encrypted != original_text
    decrypted = aes_cipher.decrypt(encrypted)
    assert decrypted == original_text


def test_decrypt_invalid_data(aes_cipher):
    assert aes_cipher.decrypt("invalid-data") is None


def test_decrypt_bad_encoding(aes_cipher):
    # Valid base64 but invalid encrypted data structure
    bad_data = base64.b64encode(b"bad-data").decode("utf-8")
    assert aes_cipher.decrypt(bad_data) is None


@patch("app.utils.crypto.config")
def test_cipher_helper(mock_config):
    mock_config.secret_key.get_secret_value.return_value = "secret"
    c = cipher()
    assert isinstance(c, AESCipher)
