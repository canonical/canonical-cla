import asyncio
import base64
import json
from datetime import datetime
from hashlib import sha256
from typing import AsyncIterator, Literal, ParamSpec, TypeVar

import httpx
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from fastapi import Request, Response
from fastapi.security import APIKeyCookie
from starlette.exceptions import HTTPException
from typing_extensions import TypedDict

from app.config import config


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
            decoded_raw = base64.b64decode(enc)
            iv = decoded_raw[: AES.block_size]
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return unpad(
                cipher.decrypt(decoded_raw[AES.block_size :]), AES.block_size
            ).decode("utf-8")
        except ValueError as e:
            return None


def cipher():
    return AESCipher(config.secret_key.get_secret_value())


T = TypeVar("T")
P = ParamSpec("P")


class EncryptedAPIKeyCookie(APIKeyCookie):

    def __init__(self, secret, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.secret = secret

    async def __call__(self, request: Request) -> str | None:
        try:
            encrypted_api_key = await super().__call__(request)
        except HTTPException:
            return None
        if encrypted_api_key is None:
            return None
        cookie_value = self.cipher.decrypt(encrypted_api_key)
        if not cookie_value:
            return None
        #  attempt to parse the value as json
        try:
            return json.loads(cookie_value)
        except json.JSONDecodeError:
            return cookie_value

    def set_cookie(
        self,
        response: Response,
        value: str = "",
        max_age: int | None = None,
        expires: datetime | str | int | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["lax", "strict", "none"] | None = "lax",
    ):
        encrypted_value = self.cipher.encrypt(value)
        response.set_cookie(
            key=self.model.name,
            value=encrypted_value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
        )

    @property
    def cipher(self):
        return AESCipher(self.secret)


async def http_client() -> AsyncIterator[httpx.AsyncClient]:

    async with httpx.AsyncClient() as client:
        yield client


class ErrorResponse(TypedDict):
    detail: str


def error_status_codes(status_code: list[int]):
    return {status: {"model": ErrorResponse} for status in status_code}
