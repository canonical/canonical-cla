import base64 as _base64
import binascii

from fastapi import HTTPException


class Base64:
    @staticmethod
    def encode(data: str | bytes) -> str:
        return _base64.b64encode(
            data.encode() if isinstance(data, str) else data
        ).decode()

    @staticmethod
    def decode(data: str, text: bool | None = True) -> str | bytes:
        try:
            output = _base64.b64decode(data.encode())
            return output.decode() if text else output
        except binascii.Error as e:
            raise HTTPException(status_code=400, detail="Invalid base64 encoding") from e

    @staticmethod
    def decode_str(data: str) -> str:
        decoded_data = Base64.decode(data)
        if isinstance(decoded_data, bytes):
            return decoded_data.decode("utf-8")
        return decoded_data
