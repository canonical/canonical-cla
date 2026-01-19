from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class OIDCMetadata(BaseModel):
    """OIDC provider metadata from discovery endpoint."""

    issuer: Annotated[
        str,
        Field(
            description="Issuer URL",
            examples=["https://login.canonical.com"],
        ),
    ]
    authorization_endpoint: Annotated[
        str,
        Field(
            description="Authorization endpoint URL",
            examples=["https://login.canonical.com/authorize"],
        ),
    ]
    token_endpoint: Annotated[
        str,
        Field(
            description="Token endpoint URL",
            examples=["https://login.canonical.com/token"],
        ),
    ]
    userinfo_endpoint: Annotated[
        str,
        Field(
            description="User info endpoint URL",
            examples=["https://login.canonical.com/userinfo"],
        ),
    ]
    jwks_uri: Annotated[
        str,
        Field(
            description="JWKS URI",
            examples=["https://login.canonical.com/jwks"],
        ),
    ]


class OIDCPendingAuthSession(BaseModel):
    """Session state stored during OIDC authentication flow."""

    state: Annotated[
        str,
        Field(
            description="State parameter for OIDC flow",
            examples=["random_state_string"],
        ),
    ]

    redirect_uri: Annotated[
        str,
        Field(
            description="The redirect URI to redirect to after authentication. This cannot be a full URL, it must be a relative path.",
            examples=["/dashboard"],
        ),
    ]


class OIDCAccessTokenSession(BaseModel):
    """Session state stored during OIDC authentication flow."""

    access_token: Annotated[
        str,
        Field(
            description="OIDC access token",
            examples=["access_token_string"],
        ),
    ]


class OIDCTokenResponse(BaseModel):
    """Response from OIDC token endpoint."""

    access_token: Annotated[
        str,
        Field(
            description="OIDC access token",
            examples=["access_token_string"],
        ),
    ]
    token_type: Annotated[
        str,
        Field(
            description="Token type",
            examples=["Bearer"],
        ),
    ]


class OIDCUserInfo(BaseModel):
    """User information from OIDC userinfo endpoint."""

    sub: Annotated[
        str,
        StringConstraints(max_length=255),
        Field(
            description="Subject identifier (unique user ID)", examples=["1ee396e6-e522-41f5-b4a4-5480d9543358 "]
        ),
    ]
    email: Annotated[
        str | None,
        StringConstraints(max_length=100),
        Field(
            description="User's email address", examples=["user@canonical.com"]
        ),
    ] = None
    email_verified: Annotated[
        bool,
        Field(description="Whether the email is verified", examples=[True]),
    ] = False
    name: Annotated[
        str | None,
        StringConstraints(max_length=100),
        Field(description="User's full name", examples=["John Doe"]),
    ] = None
    given_name: Annotated[
        str | None,
        StringConstraints(max_length=50),
        Field(description="User's given/first name", examples=["John"]),
    ] = None
    family_name: Annotated[
        str | None,
        StringConstraints(max_length=50),
        Field(description="User's family/last name", examples=["Doe"]),
    ] = None
    preferred_username: Annotated[
        str | None,
        StringConstraints(max_length=100),
        Field(description="Preferred username", examples=["jdoe"]),
    ] = None
    picture: Annotated[
        str | None,
        StringConstraints(max_length=500),
        Field(
            description="URL to user's profile picture",
            examples=["https://example.com/profile.jpg"],
        ),
    ] = None
