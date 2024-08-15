from typing import TypedDict


class GithubPendingAuthSession(TypedDict):
    state: str


class GitHubAccessTokenResponse(TypedDict):
    access_token: str
    token_type: str
    scope: str
