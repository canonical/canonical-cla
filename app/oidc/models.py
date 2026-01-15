from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class OIDCMetadata(BaseModel):
    """OIDC provider metadata from discovery endpoint."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str


class OIDCPendingAuthSession(BaseModel):
    """Session state stored during OIDC authentication flow."""

    state: str

    # The redirect URI to redirect to after authentication.
    # This cannot be a full URL, it must be a relative path.
    redirect_uri: str


class OIDCAccessTokenSession(BaseModel):
    """Session state stored during OIDC authentication flow."""

    access_token: str


class OIDCTokenResponse(BaseModel):
    """Response from OIDC token endpoint."""

    access_token: str
    token_type: str


class OIDCUserInfo(BaseModel):
    """User information from OIDC userinfo endpoint."""

    sub: Annotated[str, StringConstraints(max_length=255)] = Field(
        ..., description="Subject identifier (unique user ID)", examples=["abc123"]
    )
    email: Annotated[str | None, StringConstraints(max_length=100)] = Field(
        None, description="User's email address", examples=["user@canonical.com"]
    )
    email_verified: bool = Field(
        False, description="Whether the email is verified", examples=[True]
    )
    name: Annotated[str | None, StringConstraints(max_length=100)] = Field(
        None, description="User's full name", examples=["John Doe"]
    )
    given_name: Annotated[str | None, StringConstraints(max_length=50)] = Field(
        None, description="User's given/first name"
    )
    family_name: Annotated[str | None, StringConstraints(max_length=50)] = Field(
        None, description="User's family/last name", examples=["Doe"]
    )
    preferred_username: Annotated[str | None, StringConstraints(max_length=100)] = (
        Field(None, description="Preferred username", examples=["jdoe"])
    )
    picture: Annotated[str | None, StringConstraints(max_length=500)] = Field(
        None,
        description="URL to user's profile picture",
        examples=["https://example.com/profile.jpg"],
    )
