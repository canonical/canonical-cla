from typing import Annotated, List

from pydantic import BaseModel, ConfigDict, Field


class GithubPendingAuthSession(BaseModel):
    state: Annotated[
        str,
        Field(description="State", examples=["state_string"]),
    ]

    redirect_url: Annotated[
        str,
        Field(description="Redirect URL", examples=["https://example.com/dashboard"]),
    ]


class GitHubAccessTokenResponse(BaseModel):
    access_token: Annotated[
        str,
        Field(
            description="GitHub access token",
            examples=["access_token_string"],
        ),
    ]
    token_type: Annotated[
        str,
        Field(description="Token type", examples=["Bearer"]),
    ]
    scope: Annotated[
        str,
        Field(description="Scope", examples=["user:email"]),
    ]


class GitHubAccessTokenSession(GitHubAccessTokenResponse):
    """Access token session state stored after successful GitHub OAuth authentication."""


class GitHubEmailResponse(BaseModel):
    email: Annotated[str, Field(description="The email address")]
    verified: Annotated[bool, Field(description="Whether the email is verified")]


class GitHubProfile(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "canonical",
                "emails": ["contact@canonica.com", "contact@ubuntu.com"],
            }
        }
    )
    _id: int
    username: str = Field(..., description="GitHub username.")
    emails: list[str] = Field(
        ...,
        description="List of verified email addresses.",
    )

    def __init__(self, _id: int, **data):
        super().__init__(**data)
        self._id = _id


class GitHubRepository(BaseModel):
    full_name: str


class GitHubPullRequestHead(BaseModel):
    sha: str


class GitHubPullRequest(BaseModel):
    number: int
    head: GitHubPullRequestHead


class GitHubInstallation(BaseModel):
    id: int


class GitHubCheckRun(BaseModel):
    head_sha: str
    pull_requests: List[GitHubPullRequest] = []


class GitHubWebhookPayload(BaseModel):
    action: str
    repository: GitHubRepository
    installation: GitHubInstallation
    pull_request: GitHubPullRequest | None = None
    check_run: GitHubCheckRun | None = None


class WebhookResponse(BaseModel):
    message: str = Field(description="Message", examples=["Webhook processed"])
