import hashlib
import hmac
import re

import httpx
from fastapi import Depends, HTTPException
from gidgethub.apps import get_installation_access_token
from gidgethub.httpx import GitHubAPI

from app.cla.service import CLAService, cla_service
from app.config import config
from app.github.models import GitHubWebhookPayload, WebhookResponse
from app.http_client import http_client

LICENSE_MAP = {
    "canonical/lxd": ["Apache-2.0"],
    "canonical/lxd-ci": ["Apache-2.0"],
    "canonical/lxd-imagebuilder": ["Apache-2.0"],
}


def has_implicit_license(commit_message: str, repo_name: str) -> str:
    if repo_name not in LICENSE_MAP:
        return ""

    lines = commit_message.split("\n")
    # Skip the commit subject (first line)
    for line in lines[1:]:
        # Remove any trailing `\r` char
        line = line.rstrip("\r")
        # Accept both American and British spellings (`License` and `Licence`)
        match = re.match(r"^Licen[cs]e: ?(.+)$", line)
        if match and match.group(1) in LICENSE_MAP[repo_name]:
            return match.group(1)
    return ""


class GithubWebhookService:
    def __init__(self, cla_service: CLAService, http_client: httpx.AsyncClient):
        self.cla_service = cla_service
        self.http_client = http_client

    def verify_signature(self, payload_body: bytes, signature_header: str | None):
        """Verify that the payload was sent from GitHub by validating SHA256.

        Raise and return 403 if not authorized.

        Args:
            payload_body: original request body to verify (request.body())
            signature_header: header received from GitHub (x-hub-signature-256)

        """
        if not signature_header:
            raise HTTPException(
                status_code=403, detail="x-hub-signature-256 header is missing!"
            )

        hash_object = hmac.new(
            config.github_app.secret.get_secret_value().encode("utf-8"),
            msg=payload_body,
            digestmod=hashlib.sha256,
        )
        expected_signature = "sha256=" + hash_object.hexdigest()
        if not hmac.compare_digest(expected_signature, signature_header):
            raise HTTPException(
                status_code=403, detail="Request signatures didn't match!"
            )

    async def process_webhook(self, payload: GitHubWebhookPayload) -> WebhookResponse:
        """
        Main webhook processing function.
        Routes events to the appropriate handler.
        """
        repo_full_name = payload.repository.full_name

        # Handle pull request events for creating/updating checks
        if payload.pull_request and payload.action in [
            "opened",
            "reopened",
            "synchronize",
        ]:
            sha = payload.pull_request.head.sha
            pr_number = payload.pull_request.number
            installation_id = payload.installation.id
            await self.update_check_run(sha, repo_full_name, pr_number, installation_id)
            return WebhookResponse(message="Pull request event processed")

        # Handle the "Re-run" event from the GitHub UI
        elif payload.check_run and payload.action == "rerequested":
            sha = payload.check_run.head_sha
            if payload.check_run.pull_requests:
                pr_number = payload.check_run.pull_requests[0].number
                installation_id = payload.installation.id
                await self.update_check_run(
                    sha, repo_full_name, pr_number, installation_id
                )
                return WebhookResponse(message="Re-run event processed")
            else:
                return WebhookResponse(message="Re-run event ignored, no pull request")

        return WebhookResponse(message="Event not processed")

    async def update_check_run(
        self, sha: str, repo_full_name: str, pr_number: int, installation_id: int
    ):
        """
        Creates or updates the 'Canonical CLA' check run for a given commit.
        """
        owner, _ = repo_full_name.split("/")

        g = await self._get_github_api_for_installation(owner, installation_id)

        commit_authors = await self._get_commit_authors(g, repo_full_name, pr_number)

        authors_cla_status = await self._check_authors_cla(commit_authors)

        conclusion, output = self._create_check_run_output(authors_cla_status)

        await self._update_or_create_check_run(
            g, repo_full_name, sha, conclusion, output
        )

    async def _get_github_api_for_installation(
        self, owner: str, installation_id: int
    ) -> GitHubAPI:
        """Get an authenticated GitHubAPI instance for an installation."""
        gh = GitHubAPI(self.http_client, requester=owner)
        access_token_response = await get_installation_access_token(
            gh,
            installation_id=str(installation_id),
            app_id=str(config.github_app.id),
            private_key=config.github_app.private_key.get_secret_value(),
        )

        return GitHubAPI(
            self.http_client,
            requester=owner,
            oauth_token=access_token_response["token"],
        )

    async def _get_commit_authors(
        self, g: GitHubAPI, repo_full_name: str, pr_number: int
    ) -> dict:
        """Collect commit authors from a pull request."""
        commit_authors = {}
        pr_commits_url = f"/repos/{repo_full_name}/pulls/{pr_number}/commits"
        commits = g.getiter(pr_commits_url)

        async for commit_data in commits:
            commit = await g.getitem(commit_data["url"])
            # Check for implicit license
            if has_implicit_license(commit["commit"]["message"], repo_full_name):
                continue

            author_email = commit["commit"]["author"]["email"]
            if not author_email:
                continue

            author_login = commit["author"]["login"] if commit["author"] else None

            if author_email not in commit_authors:
                commit_authors[author_email] = {
                    "username": author_login,
                    "signed": False,
                }
        return commit_authors

    async def _check_authors_cla(self, commit_authors: dict) -> dict:
        """
        Check CLA status for commit authors and return the updated authors dict.
        """
        # Exclude bot accounts
        for _email, author in commit_authors.items():
            username = author["username"]
            if username and username.endswith("[bot]"):
                author["signed"] = True

        # Check CLA for remaining authors
        emails_to_check = []
        usernames_to_check = []
        for email, author in commit_authors.items():
            if not author["signed"]:
                emails_to_check.append(email)
                if author["username"]:
                    usernames_to_check.append(author["username"])

        if not emails_to_check:
            return commit_authors

        cla_status = await self.cla_service.check_cla(
            emails=emails_to_check,
            github_usernames=usernames_to_check,
            launchpad_usernames=[],
        )

        for email, author in commit_authors.items():
            if not author["signed"]:
                username = author["username"]
                is_signed = cla_status.emails.get(email, False) or (
                    username and cla_status.github_usernames.get(username, False)
                )

                if is_signed:
                    author["signed"] = True
        return commit_authors

    def _create_check_run_output(self, authors_cla_status: dict) -> tuple[str, dict]:
        """
        Create the output for the check run based on authors' CLA status.
        """
        signed_authors = []
        unsigned_authors = []

        sorted_authors = sorted(
            authors_cla_status.items(),
            key=lambda item: item[1]["username"] or "",
        )

        for email, author in sorted_authors:
            username = author["username"] or "Unknown user"
            if author["signed"]:
                signed_authors.append(f"- {username} ✓ (CLA signed)")
            else:
                unsigned_authors.append(f"- {username} ({email}) ✗ (CLA not signed)")

        if not unsigned_authors:
            conclusion = "success"
            summary = "All contributors have signed the CLA. Thank you!"
            if signed_authors:
                summary += "\n\n" + "\n".join(signed_authors)
            output = {
                "title": "All contributors have signed the CLA.",
                "summary": summary,
            }
        else:
            conclusion = "failure"
            all_authors_status = unsigned_authors + signed_authors
            summary = (
                "Some commit authors have not signed the Canonical CLA which is "
                "required to get this contribution merged on this project.\n\n"
                "The following shows the status of all commit authors:\n"
                + "\n".join(all_authors_status)
                + "\n\nPlease head over to "
                "https://ubuntu.com/legal/contributors to sign the CLA."
            )
            output = {"title": "CLA Check Failed", "summary": summary}
        return conclusion, output

    async def _update_or_create_check_run(
        self,
        g: GitHubAPI,
        repo_full_name: str,
        sha: str,
        conclusion: str,
        output: dict,
    ):
        """Create or update the GitHub check run."""
        check_run_name = "Canonical CLA"
        check_runs_url = f"/repos/{repo_full_name}/check-runs"
        commit_check_runs_url = f"/repos/{repo_full_name}/commits/{sha}/check-runs"
        check_runs = await g.getitem(
            commit_check_runs_url,
        )

        existing_run = None
        for run in check_runs["check_runs"]:
            if run["name"] == check_run_name:
                existing_run = run
                break

        if existing_run:
            await g.patch(
                existing_run["url"],
                data={
                    "status": "completed",
                    "conclusion": conclusion,
                    "output": output,
                },
            )
        else:
            await g.post(
                check_runs_url,
                data={
                    "name": check_run_name,
                    "head_sha": sha,
                    "status": "completed",
                    "conclusion": conclusion,
                    "output": output,
                },
            )


async def github_webhook_service(
    cla_service: CLAService = Depends(cla_service),
    http_client: httpx.AsyncClient = Depends(http_client),
) -> "GithubWebhookService":
    return GithubWebhookService(cla_service, http_client)
