from typing import TypedDict

from pydantic import BaseModel, Field, ConfigDict


class GithubPendingAuthSession(TypedDict):
    state: str


class GitHubAccessTokenResponse(TypedDict):
    access_token: str
    token_type: str
    scope: str


class GithubProfile(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 123456,
                "username": "canonical",
                "emails": ["contact@canonica.com", "contact@ubuntu.com"],
            }
        }
    )
    id: int = Field(
        ...,
        description="GitHub user ID.",
    )
    username: str = Field(..., description="GitHub username.")
    emails: list[str] = Field(
        ...,
        description="List of verified email addresses.",
    )
