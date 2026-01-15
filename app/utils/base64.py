import base64
import binascii

from fastapi import HTTPException


class Base64:
    @staticmethod
    def encode(data: str) -> str:
        return base64.b64encode(data.encode()).decode()

    @staticmethod
    def decode(data: str, text: bool | None = True) -> str | bytes:
        try:
            output = base64.b64decode(data.encode())
            return output.decode() if text else output
        except binascii.Error:
            raise HTTPException(status_code=400, detail="Invalid base64 encoding")
