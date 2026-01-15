import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from fastapi import Request, Response
from fastapi.security import APIKeyCookie
from pydantic import BaseModel, ValidationError
from starlette.exceptions import HTTPException

from app.utils.crypto import AESCipher


class EncryptedAPIKeyCookie(APIKeyCookie):
    """
    A cookie that is encrypted and decrypted using the AES cipher.

    When the cookie is stored as JSON, it is parsed (typically into a dictionary).
    """

    def __init__(self, secret, name: str, *args, **kwargs):
        super().__init__(*args, **kwargs, name=name)
        self.name = name
        self.secret = secret

    async def __call__(self, request: Request) -> str | dict[str, Any] | None:  # type: ignore[override]
        try:
            encrypted_api_key = await super().__call__(request)
        except HTTPException:
            return None
        if encrypted_api_key is None:
            return None
        cookie_value = self.cipher.decrypt(encrypted_api_key)
        print("--------------------------------")
        print(cookie_value)
        print("--------------------------------")

        if not cookie_value:
            return None
        #  attempt to parse the value as json
        try:
            parsed = json.loads(cookie_value)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return cookie_value

    def set_cookie(
        self,
        response: Response,
        value: str | dict[str, Any] = "",
        max_age: int | None = None,
        expires: datetime | str | int | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["lax", "strict", "none"] | None = "lax",
    ):
        if isinstance(value, dict):
            value = json.dumps(value)
        encrypted_value = self.cipher.encrypt(value)
        response.set_cookie(
            key=self.name,
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


TModel = TypeVar("TModel", bound=BaseModel)


class APIKeyCookieModel(EncryptedAPIKeyCookie, Generic[TModel], ABC):
    """
    `EncryptedAPIKeyCookie` variant that validates dict JSON payloads into a Pydantic model.

    - If `EncryptedAPIKeyCookie` returns a `str` (non-JSON or invalid JSON), this returns `None`.
    - If it returns a `dict`, this tries `model_validate(...)` and returns the model.
    - If validation fails, this returns `None`.

    Example:

    ```python
    from fastapi import Depends, FastAPI
    from pydantic import BaseModel

    from app.utils.api_cookie import APIKeyCookieModel

    app = FastAPI()


    class SessionData(BaseModel):
        user_id: int
        org: str | None = None


    class SessionCookie(APIKeyCookieModel[SessionData]):
        @property
        def payload_model(self) -> type[SessionData]:
            return SessionData


    cookie_scheme = SessionCookie(secret="change-me", name="session")


    @app.get("/items/")
    async def read_items(session: SessionData | None = Depends(cookie_scheme)):
        return {"session": session.model_dump() if session else None}
    ```
    """

    @property
    @abstractmethod
    def payload_model(self) -> type[TModel]:
        raise NotImplementedError

    async def __call__(self, request: Request) -> TModel | None:  # type: ignore[override]
        value = await super().__call__(request)
        if isinstance(value, str) or value is None:
            return None

        if not isinstance(value, dict):
            return None

        try:
            return self.payload_model.model_validate(value)
        except ValidationError:
            return None

    def set_cookie(
        self,
        response: Response,
        value: str | dict[str, Any] | TModel = "",
        max_age: int | None = None,
        expires: datetime | str | int | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["lax", "strict", "none"] | None = "lax",
    ):
        if isinstance(value, BaseModel):
            value = value.model_dump()
        super().set_cookie(
            response=response,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
        )
