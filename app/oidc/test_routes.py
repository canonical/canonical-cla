from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from app.database.models import Role, UserRole
from app.oidc.models import OIDCPendingAuthSession, OIDCProfile, OIDCUserInfo
from app.oidc.routes import oidc_callback, oidc_login, oidc_logout, oidc_profile


@pytest.fixture
def mock_oidc_service():
    return AsyncMock()


@pytest.mark.asyncio
async def test_oidc_login(mock_oidc_service):
    await oidc_login(redirect_uri="/home", oidc_service=mock_oidc_service)
    mock_oidc_service.login.assert_called_once()
    # Verify arguments
    _, kwargs = mock_oidc_service.login.call_args
    assert kwargs["redirect_uri"] == "http://cla.localhost/home"


@pytest.mark.asyncio
async def test_oidc_login_default_redirect(mock_oidc_service):
    await oidc_login(redirect_uri=None, oidc_service=mock_oidc_service)
    _, kwargs = mock_oidc_service.login.call_args
    assert kwargs["redirect_uri"] == "/oidc/profile"


@pytest.mark.asyncio
async def test_oidc_callback_success(mock_oidc_service):
    session = OIDCPendingAuthSession(state="test_state", redirect_uri="/home")
    await oidc_callback(
        code="code",
        state="test_state",
        oidc_pending_auth_session=session,
        oidc_service=mock_oidc_service,
    )
    mock_oidc_service.callback.assert_called_once()
    args, _ = mock_oidc_service.callback.call_args
    assert args[0] == "code"
    assert args[2] == "/home"


@pytest.mark.asyncio
async def test_oidc_callback_missing_session(mock_oidc_service):
    with pytest.raises(HTTPException) as exc:
        await oidc_callback(
            code="code",
            state="test_state",
            oidc_pending_auth_session=None,
            oidc_service=mock_oidc_service,
        )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_oidc_callback_missing_params(mock_oidc_service):
    session = OIDCPendingAuthSession(state="test_state", redirect_uri="/home")
    with pytest.raises(HTTPException) as exc:
        await oidc_callback(
            code=None,
            state="test_state",
            oidc_pending_auth_session=session,
            oidc_service=mock_oidc_service,
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_oidc_callback_state_mismatch(mock_oidc_service):
    session = OIDCPendingAuthSession(state="test_state", redirect_uri="/home")
    with pytest.raises(HTTPException) as exc:
        await oidc_callback(
            code="code",
            state="wrong_state",
            oidc_pending_auth_session=session,
            oidc_service=mock_oidc_service,
        )
    assert exc.value.status_code == 401
    assert "OAuth state mismatch" in exc.value.detail


@pytest.mark.asyncio
async def test_oidc_callback_error_description(mock_oidc_service):
    session = OIDCPendingAuthSession(state="test_state", redirect_uri="/home")
    with pytest.raises(HTTPException) as exc:
        await oidc_callback(
            code="code",
            state="test_state",
            error_description="access_denied",
            oidc_pending_auth_session=session,
            oidc_service=mock_oidc_service,
        )
    assert exc.value.status_code == 400
    assert "access_denied" in exc.value.detail


@pytest.mark.asyncio
async def test_oidc_profile_with_role():
    user = OIDCUserInfo(sub="123", email="user@example.com", email_verified=True)
    mock_user_role = Mock(spec=UserRole)
    mock_user_role.role = Role.ADMIN
    mock_user_role_repository = AsyncMock()
    mock_user_role_repository.get_user_role.return_value = mock_user_role

    result = await oidc_profile(
        oidc_user=user, user_role_repository=mock_user_role_repository
    )

    assert isinstance(result, OIDCProfile)
    assert result.user == user
    assert result.role == Role.ADMIN
    mock_user_role_repository.get_user_role.assert_called_once_with("user@example.com")


@pytest.mark.asyncio
async def test_oidc_profile_without_role():
    user = OIDCUserInfo(sub="123", email="user@example.com", email_verified=True)
    mock_user_role_repository = AsyncMock()
    mock_user_role_repository.get_user_role.return_value = None

    result = await oidc_profile(
        oidc_user=user, user_role_repository=mock_user_role_repository
    )

    assert isinstance(result, OIDCProfile)
    assert result.user == user
    assert result.role is None
    mock_user_role_repository.get_user_role.assert_called_once_with("user@example.com")


@pytest.mark.asyncio
async def test_oidc_logout(mock_oidc_service):
    await oidc_logout(redirect_uri="/login", oidc_service=mock_oidc_service)
    mock_oidc_service.logout.assert_called_once_with("/login")
