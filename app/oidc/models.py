from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class OIDCMetadata(TypedDict):
    """OIDC provider metadata from discovery endpoint."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str


class OIDCPendingAuthSession(TypedDict):
    """Session state stored during OIDC authentication flow."""

    state: str
    nonce: str
    redirect_url: str | None


class OIDCTokenResponse(TypedDict):
    """Response from OIDC token endpoint."""

    access_token: str
    token_type: str
    expires_in: int
    id_token: str
    refresh_token: str | None


class OIDCUserInfo(BaseModel):
    """User information from OIDC userinfo endpoint."""

    sub: str = Field(
        ..., description="Subject identifier (unique user ID)", examples=["abc123"]
    )
    email: str | None = Field(
        None, description="User's email address", examples=["user@canonical.com"]
    )
    email_verified: bool = Field(
        False, description="Whether the email is verified", examples=[True]
    )
    name: str | None = Field(
        None, description="User's full name", examples=["John Doe"]
    )
    given_name: str | None = Field(None, description="User's given/first name")
    family_name: str | None = Field(
        None, description="User's family/last name", examples=["Doe"]
    )
    preferred_username: str | None = Field(
        None, description="Preferred username", examples=["jdoe"]
    )
    picture: str | None = Field(
        None,
        description="URL to user's profile picture",
        examples=["https://example.com/profile.jpg"],
    )


class OIDCProfile(BaseModel):
    """Processed OIDC profile for the application."""

    sub: str = Field(
        ..., description="Subject identifier (unique user ID)", examples=["abc123"]
    )
    email: str | None = Field(
        None, description="User's email address", examples=["user@canonical.com"]
    )
    email_verified: bool = Field(
        False, description="Whether the email is verified", examples=[True]
    )
    name: str | None = Field(
        None, description="User's full name", examples=["John Doe"]
    )
    username: str | None = Field(
        None, description="Preferred username", examples=["jdoe"]
    )
    picture: str | None = Field(
        None,
        description="URL to user's profile picture",
        examples=["https://example.com/profile.jpg"],
    )
    given_name: str | None = Field(
        None, description="User's given/first name", examples=["John"]
    )
    family_name: str | None = Field(
        None, description="User's family/last name", examples=["Doe"]
    )
