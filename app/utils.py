import base64
import binascii
import ipaddress
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime
from hashlib import sha256
from typing import Literal, ParamSpec, TypeVar, cast
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from fastapi import Request, Response
from fastapi.datastructures import Headers
from fastapi.security import APIKeyCookie
from starlette.exceptions import HTTPException
from typing_extensions import TypedDict

from app.config import config
from app.http_client import HTTPClient

logger = logging.getLogger(__name__)


class AESCipher:
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
            decoded_raw = cast(bytes, Base64.decode(enc, text=False))
            iv = decoded_raw[: AES.block_size]
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return unpad(
                cipher.decrypt(decoded_raw[AES.block_size :]), AES.block_size
            ).decode("utf-8")
        except (ValueError, HTTPException):
            return None


def cipher():
    return AESCipher(config.secret_key.get_secret_value())


class Base64:
    @staticmethod
    def encode(data: str) -> str:
        return base64.b64encode(data.encode()).decode()

    @staticmethod
    def decode(data: str, text: bool | None = True) -> str | bytes:
        try:
            output = base64.b64decode(data.encode())
            return output.decode() if text else output
        except binascii.Error as err:
            raise HTTPException(
                status_code=400, detail="Invalid base64 encoding"
            ) from err


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
    async with HTTPClient() as client:
        yield client


class ErrorResponse(TypedDict):
    detail: str


def error_status_codes(status_code: list[int]):
    return {status: {"model": ErrorResponse} for status in status_code}


def update_query_params(url: str, **params) -> str:
    url_parts = list(urlparse(url))
    query = dict(parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return str(urlunparse(url_parts))


def ip_address(request: Request | None = None, headers: Headers | None = None) -> str:
    """
    Extract the client's IP address from the request headers.
    This takes into account the possibility of the request being forwarded by a proxy.
    """
    if request is None:
        raise ValueError("Request must be provided")
    headers = headers or request.headers
    if not headers:
        raise ValueError("Either request or headers must be provided")
    ip = None
    if "x-original-forwarded-for" in headers:
        ip = headers["x-original-forwarded-for"].split(",")[0]
    elif "x-forwarded-for" in headers:
        ip = headers["x-forwarded-for"].split(",")[0]
    else:
        request_client = request.client
        if not request_client:
            raise ValueError(
                "Request must be provided when headers don't contain IP info"
            )
        ip = request_client.host

    if _is_local_request(ip):
        # consider the custom header only if the request is local (ubuntu.com backend proxy)
        return headers.get(
            "custom-forwarded-for", headers.get("x-custom-forwarded-for", ip)
        )
    else:
        return ip


def is_local_request(request: Request) -> bool:
    client_addr = ip_address(request)
    return _is_local_request(client_addr)


def _is_local_request(ip: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_loopback or ip_obj.is_private
    except ValueError:
        return False
