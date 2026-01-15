import base64
from hashlib import sha256

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from fastapi import HTTPException

from app.config import config
from app.utils.base64 import Base64


class AESCipher(object):
    def __init__(self, key: str):
        self.bs = AES.block_size
        self.key = sha256(key.encode()).digest()

    def encrypt(self, raw: str) -> str:
        encoded_raw = pad(raw.encode(), AES.block_size)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(encoded_raw)).decode("utf-8")

    def decrypt(self, enc: str) -> str | None:
        try:
            decoded_raw = Base64.decode(enc, text=False)
            if isinstance(decoded_raw, str):
                decoded_raw = decoded_raw.encode()
            iv = decoded_raw[: AES.block_size]
            cipher = AES.new(
                self.key,
                AES.MODE_CBC,
                iv,
            )
            return unpad(
                cipher.decrypt(decoded_raw[AES.block_size :]), AES.block_size
            ).decode("utf-8")
        except (ValueError, HTTPException):
            return None


def cipher():
    return AESCipher(config.secret_key.get_secret_value())
