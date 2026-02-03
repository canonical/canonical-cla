from typing import Annotated

from pydantic import BaseModel, Field


class LaunchpadPersonResponse(BaseModel):
    id: Annotated[
        str, Field(description="The id", examples=["tag:launchpad.net:2008:redacted"])
    ]
    name: Annotated[str, Field(description="The name", examples=["canonical"])]
    preferred_email_address_link: Annotated[
        str,
        Field(
            description="The preferred email address link",
            examples=[
                "https://api.launchpad.net/1.0/~canonical/+email/contact@canonical.com"
            ],
        ),
    ]
    confirmed_email_addresses_collection_link: Annotated[
        str,
        Field(
            description="The confirmed email addresses collection link",
            examples=[
                "https://api.launchpad.net/1.0/~canonical/confirmed_email_addresses"
            ],
        ),
    ]


class LaunchpadEmailResponse(BaseModel):
    self_link: Annotated[
        str,
        Field(
            description="The self link",
            examples=[
                "https://api.launchpad.net/1.0/~canonical/+email/contact@canonical.com"
            ],
        ),
    ]
    web_link: Annotated[
        str,
        Field(
            description="The web link",
            examples=["https://launchpad.net/~canonical/+email/contact@canonical.com"],
        ),
    ]
    resource_type_link: Annotated[
        str,
        Field(
            description="The resource type link",
            examples=[
                "https://api.launchpad.net/1.0/~canonical/+email/contact@canonical.com"
            ],
        ),
    ]
    email: Annotated[
        str, Field(description="The email", examples=["contact@canonical.com"])
    ]
    person_link: Annotated[
        str,
        Field(
            description="The person link",
            examples=["https://api.launchpad.net/1.0/~canonical"],
        ),
    ]
    http_etag: Annotated[str, Field(description="The http etag", examples=["etag"])]


class LaunchpadEmailListResponse(BaseModel):
    entries: Annotated[
        list[LaunchpadEmailResponse],
        Field(
            description="The entries",
            examples=[
                LaunchpadEmailResponse(
                    self_link="https://api.launchpad.net/1.0/~canonical/+email/contact@canonical.com",
                    web_link="https://launchpad.net/~canonical/+email/contact@canonical.com",
                    resource_type_link="https://api.launchpad.net/1.0/~canonical/+email/contact@canonical.com",
                    email="contact@canonical.com",
                    person_link="https://api.launchpad.net/1.0/~canonical",
                    http_etag="etag",
                )
            ],
        ),
    ]
    start: Annotated[int, Field(description="The start", examples=[0])]
    total_size: Annotated[int, Field(description="The total size", examples=[1])]
    resource_type_link: Annotated[
        str,
        Field(
            description="The resource type link",
            examples=[
                "https://api.launchpad.net/1.0/~canonical/+email/contact@canonical.com"
            ],
        ),
    ]


class LaunchpadRequestTokenResponse(BaseModel):
    """Response from Launchpad request token endpoint, used to obtain an OAuth token and secret during the authentication flow."""

    oauth_token: Annotated[
        str, Field(description="The OAuth token", examples=["oauth_token_string"])
    ]
    oauth_token_secret: Annotated[
        str,
        Field(description="The OAuth token secret", examples=["oauth_secret_string"]),
    ]
    oauth_token_consumer: Annotated[
        str,
        Field(
            description="The OAuth token consumer", examples=["oauth_consumer_string"]
        ),
    ]


class LaunchpadAccessTokenResponse(BaseModel):
    """Response from Launchpad access token endpoint, used to obtain an access token after successful authentication."""

    oauth_token: Annotated[
        str, Field(description="The OAuth token", examples=["oauth_token_string"])
    ]
    oauth_token_secret: Annotated[
        str,
        Field(description="The OAuth token secret", examples=["oauth_secret_string"]),
    ]


class AccessTokenSession(BaseModel):
    """Access token session state stored after successful Launchpad OAuth authentication."""

    oauth_token: Annotated[
        str, Field(description="The OAuth token", examples=["oauth_token_string"])
    ]
    oauth_token_secret: Annotated[
        str,
        Field(description="The OAuth token secret", examples=["oauth_secret_string"]),
    ]


class RequestTokenSession(BaseModel):
    """Session state stored during Launchpad OAuth authentication flow."""

    oauth_token: Annotated[str, Field(description="The OAuth token")]
    oauth_token_secret: Annotated[str, Field(description="The OAuth token secret")]
    state: Annotated[str, Field(description="The OAuth state")]
    redirect_url: Annotated[str, Field(description="The redirect URL")]


class LaunchpadProfile(BaseModel):
    """Launchpad user profile."""

    _id: str
    username: Annotated[
        str, Field(description="Launchpad username", examples=["canonical"])
    ]
    emails: Annotated[
        list[str],
        Field(
            description="List of verified email addresses",
            examples=["contact@canonica.com", "contact@ubuntu.com"],
        ),
    ]

    def __init__(self, _id: str, **data):
        super().__init__(_id=_id, **data)
        self._id = _id
