from unittest.mock import MagicMock

import pytest

from app.utils.request import (
    ErrorResponse,
    error_status_codes,
    ip_address,
    is_local_request,
    update_query_params,
)


def test_error_status_codes():
    codes = [400, 404]
    result = error_status_codes(codes)
    assert result == {400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}


def test_update_query_params():
    url = "http://example.com/path?param1=value1"
    new_url = update_query_params(url, param2="value2")
    assert "param1=value1" in new_url
    assert "param2=value2" in new_url

    # Test updating existing param
    new_url_update = update_query_params(url, param1="new_value")
    assert "param1=new_value" in new_url_update


@pytest.fixture
def mock_request():
    # We don't use spec=Request because it complicates property mocking for client
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "1.2.3.4"
    # Headers must not be empty for ip_address function
    request.headers = {"host": "example.com"}
    return request


def test_ip_address_no_headers(mock_request):
    mock_request.client.host = "1.2.3.4"
    # Ensure headers are not empty but don't contain forwarded info
    mock_request.headers = {"host": "example.com"}

    assert ip_address(mock_request) == "1.2.3.4"


def test_ip_address_x_forwarded_for(mock_request):
    mock_request.headers = {"x-forwarded-for": "5.6.7.8, 1.2.3.4"}

    assert ip_address(mock_request) == "5.6.7.8"


def test_ip_address_x_original_forwarded_for(mock_request):
    mock_request.headers = {
        "x-original-forwarded-for": "9.10.11.12",
        "x-forwarded-for": "5.6.7.8",
    }

    assert ip_address(mock_request) == "9.10.11.12"


def test_ip_address_local_request_custom_header(mock_request):
    mock_request.client.host = "127.0.0.1"
    mock_request.headers = {"custom-forwarded-for": "100.100.100.100"}

    # Since client is local, it should respect custom-forwarded-for
    assert ip_address(mock_request) == "100.100.100.100"


def test_ip_address_non_local_ignores_custom_header(mock_request):
    mock_request.client.host = "8.8.8.8"  # Public IP
    mock_request.headers = {"custom-forwarded-for": "100.100.100.100"}

    # Should ignore custom header because client is not local
    assert ip_address(mock_request) == "8.8.8.8"


def test_is_local_request_loopback(mock_request):
    mock_request.client.host = "127.0.0.1"
    mock_request.headers = {"host": "localhost"}
    assert is_local_request(mock_request) is True


def test_is_local_request_private(mock_request):
    mock_request.client.host = "192.168.1.1"
    mock_request.headers = {"host": "internal"}
    assert is_local_request(mock_request) is True


def test_is_local_request_public(mock_request):
    mock_request.client.host = "8.8.8.8"
    mock_request.headers = {"host": "public"}
    assert is_local_request(mock_request) is False


def test_ip_address_missing_request():
    with pytest.raises(ValueError, match="No request provided"):
        ip_address(None)


def test_ip_address_missing_headers(mock_request):
    mock_request.headers = {}

    assert ip_address(mock_request) == "1.2.3.4"
