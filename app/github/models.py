from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict


class GithubPendingAuthSession(TypedDict):
    state: str


class GitHubAccessTokenResponse(TypedDict):
    access_token: str
    token_type: str
    scope: str


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
    pull_request: Optional[GitHubPullRequest] = None
    check_run: Optional[GitHubCheckRun] = None
