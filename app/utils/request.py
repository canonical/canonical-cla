import ipaddress
import logging
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from fastapi import Request
from starlette.datastructures import Headers
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


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
    if not request or not request.client:
        raise ValueError("No request provided")
    headers = headers or request.headers
    ip = None
    if "x-original-forwarded-for" in headers:
        ip = headers["x-original-forwarded-for"].split(",")[0]
    elif "x-forwarded-for" in headers:
        ip = headers["x-forwarded-for"].split(",")[0]
    else:
        ip = request.client.host

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
