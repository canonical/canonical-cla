import re

from fastapi import Depends, Response
from github import Github, GithubIntegration

from app.cla.service import CLAService, cla_service
from app.config import config

GITGUB_INTEGRATION = GithubIntegration(
    config.github_app.id,
    config.github_app.private_key.get_secret_value(),
)

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


def get_github_client(owner: str, repo_name: str):
    token = GITGUB_INTEGRATION.get_access_token(
        GITGUB_INTEGRATION.get_repo_installation(owner, repo_name).id
    ).token
    git_connection = Github(login_or_token=token)
    return git_connection


class GithubWebhookService:
    def __init__(self, cla_service: CLAService):
        self.cla_service = cla_service

    async def process_webhook(self, payload: dict):
        """
        Main webhook processing function.
        Routes events to the appropriate handler.
        """
        action = payload.get("action")
        repo_full_name = payload["repository"]["full_name"]

        # Handle pull request events for creating/updating checks
        if "pull_request" in payload and action in [
            "opened",
            "reopened",
            "synchronize",
        ]:
            sha = payload["pull_request"]["head"]["sha"]
            pr_number = payload["pull_request"]["number"]
            await self.update_check_run(sha, repo_full_name, pr_number)
            return Response(
                content="Pull request event processed", status_code=200
            )

        # Handle the "Re-run" event from the GitHub UI
        elif "check_run" in payload and action == "rerequested":
            sha = payload["check_run"]["head_sha"]
            if payload["check_run"]["pull_requests"]:
                pr_number = payload["check_run"]["pull_requests"][0]["number"]
                await self.update_check_run(sha, repo_full_name, pr_number)
                return Response(
                    content="Re-run event processed", status_code=200
                )
            else:
                return Response(
                    content="Re-run event ignored, no pull request",
                    status_code=200,
                )

        return Response(content="Event not processed", status_code=200)

    async def update_check_run(
        self, sha: str, repo_full_name: str, pr_number: int
    ):
        """
        Creates or updates the 'Canonical CLA' check run for a given commit.
        """
        owner, repo_name = repo_full_name.split("/")

        g = get_github_client(owner, repo_name)
        repo = g.get_repo(repo_full_name)

        # Collect commit authors
        commit_authors = {}
        pr = repo.get_pull(pr_number)
        commits = pr.get_commits()

        for commit in commits:
            # Check for implicit license
            if has_implicit_license(commit.commit.message, repo_full_name):
                continue

            author_email = commit.commit.author.email
            if not author_email:
                continue

            author_login = commit.author.login if commit.author else None

            if author_email not in commit_authors:
                commit_authors[author_email] = {
                    "username": author_login,
                    "signed": False,
                }

        # Exclude bot accounts
        for email, author in commit_authors.items():
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

        unsigned_authors = []

        if emails_to_check:
            cla_status = await self.cla_service.check_cla(
                emails=emails_to_check,
                github_usernames=usernames_to_check,
                launchpad_usernames=[],
            )

            for email, author in commit_authors.items():
                if not author["signed"]:
                    username = author["username"]
                    is_signed = cla_status.emails.get(
                        email, False
                    ) or (
                        username
                        and cla_status.github_usernames.get(username, False)
                    )

                    if is_signed:
                        author["signed"] = True
                    else:
                        unsigned_authors.append(
                            f"- {username or 'Unknown user'} ({email})"
                        )

        # Determine conclusion and output
        if not unsigned_authors:
            conclusion = "success"
            output = {
                "title": "All contributors have signed the CLA.",
                "summary": "Thank you!",
            }
        else:
            conclusion = "failure"
            summary = (
                "Some commit authors have not signed the Canonical CLA which is "
                "required to get this contribution merged on this project.\n\n"
                "The following authors have not signed the CLA:\n"
                + "\n".join(unsigned_authors)
                + "\n\nPlease head over to "
                "https://ubuntu.com/legal/contributors to sign the CLA."
            )
            output = {"title": "CLA Check Failed", "summary": summary}

        # Create or update check run
        check_run_name = "Canonical CLA"
        commit = repo.get_commit(sha=sha)
        existing_run = None
        for run in commit.get_check_runs():
            if run.name == check_run_name:
                existing_run = run
                break

        if existing_run:
            existing_run.edit(
                status="completed", conclusion=conclusion, output=output
            )
        else:
            repo.create_check_run(
                name=check_run_name,
                head_sha=sha,
                status="completed",
                conclusion=conclusion,
                output=output,
            )


async def github_webhook_service(
    cla_service: CLAService = Depends(cla_service),
) -> "GithubWebhookService":
    return GithubWebhookService(cla_service)
