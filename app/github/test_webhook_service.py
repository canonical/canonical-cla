import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.config import config
from app.database.models import ExcludedProject, ProjectPlatform
from app.github.webhook_service import GithubWebhookService


@pytest.fixture
def cla_service_mock():
    return AsyncMock()


@pytest.fixture
def http_client_mock():
    return AsyncMock()


@pytest.fixture
def excluded_project_repository_mock():
    return AsyncMock()


@pytest.fixture
def service(cla_service_mock, http_client_mock, excluded_project_repository_mock):
    return GithubWebhookService(
        cla_service_mock, http_client_mock, excluded_project_repository_mock
    )


class TestVerifySignature:
    def test_verify_signature_valid(self, service: GithubWebhookService):
        payload_body = b'{"foo": "bar"}'
        secret = config.github_app.secret.get_secret_value().encode("utf-8")
        hash_object = hmac.new(secret, msg=payload_body, digestmod=hashlib.sha256)
        expected_signature = "sha256=" + hash_object.hexdigest()

        try:
            service.verify_signature(payload_body, expected_signature)
        except HTTPException:
            pytest.fail("verify_signature raised HTTPException unexpectedly!")

    def test_verify_signature_invalid(self, service: GithubWebhookService):
        payload_body = b'{"foo": "bar"}'
        signature_header = "sha256=invalid_signature"

        with pytest.raises(HTTPException) as excinfo:
            service.verify_signature(payload_body, signature_header)
        assert excinfo.value.status_code == 403
        assert "Request signatures didn't match!" in str(excinfo.value.detail)

    def test_verify_signature_missing_header(self, service: GithubWebhookService):
        payload_body = b'{"foo": "bar"}'

        with pytest.raises(HTTPException) as excinfo:
            service.verify_signature(payload_body, None)
        assert excinfo.value.status_code == 403
        assert "x-hub-signature-256 header is missing!" in str(excinfo.value.detail)


class TestProcessWebhook:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("action", ["opened", "reopened", "synchronize"])
    async def test_process_webhook_pr_events(
        self, service: GithubWebhookService, action: str
    ):
        payload = MagicMock()
        payload.repository.full_name = "canonical/lxd"
        payload.pull_request.head.sha = "test_sha"
        payload.pull_request.number = 123
        payload.installation.id = 456
        payload.action = action
        payload.check_run = None

        with patch.object(
            service, "update_check_run", new_callable=AsyncMock
        ) as update_check_run_mock:
            result = await service.process_webhook(payload)
            assert result.message == "Pull request event processed"
            update_check_run_mock.assert_awaited_once_with(
                "test_sha", "canonical/lxd", 123, installation_id=456
            )

    @pytest.mark.asyncio
    async def test_process_webhook_check_run_rerequested(
        self, service: GithubWebhookService
    ):
        payload = MagicMock()
        payload.pull_request = None
        payload.check_run.head_sha = "test_sha"
        payload.check_run.pull_requests = [MagicMock(number=123)]
        payload.repository.full_name = "canonical/lxd"
        payload.installation.id = 456
        payload.action = "rerequested"

        with patch.object(
            service, "update_check_run", new_callable=AsyncMock
        ) as update_check_run_mock:
            result = await service.process_webhook(payload)
            assert result.message == "Re-run event processed"
            update_check_run_mock.assert_awaited_once_with(
                "test_sha", "canonical/lxd", 123, installation_id=456
            )

    @pytest.mark.asyncio
    async def test_process_webhook_check_run_rerequested_no_pr(
        self, service: GithubWebhookService
    ):
        payload = MagicMock()
        payload.pull_request = None
        payload.check_run.head_sha = "test_sha"
        payload.check_run.pull_requests = []
        payload.repository.full_name = "canonical/lxd"
        payload.installation.id = 456
        payload.action = "rerequested"

        with patch.object(
            service, "update_check_run", new_callable=AsyncMock
        ) as update_check_run_mock:
            result = await service.process_webhook(payload)
            assert result.message == "Re-run event ignored, no pull request"
            update_check_run_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_webhook_ignored_event(self, service: GithubWebhookService):
        payload = MagicMock()
        payload.pull_request = None
        payload.check_run = None
        payload.merge_group = None
        payload.action = "some_other_action"

        with patch.object(
            service, "update_check_run", new_callable=AsyncMock
        ) as update_check_run_mock:
            result = await service.process_webhook(payload)
            assert result.message == "Event not processed"
            update_check_run_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_webhook_merge_group_checks_requested(
        self, service: GithubWebhookService
    ):
        payload = MagicMock()
        payload.pull_request = None
        payload.check_run = None
        payload.merge_group.head_sha = "merge_group_sha"
        payload.repository.full_name = "canonical/lxd"
        payload.installation.id = 456
        payload.action = "checks_requested"

        with patch.object(
            service, "update_check_run", new_callable=AsyncMock
        ) as update_check_run_mock:
            result = await service.process_webhook(payload)
            assert result.message == "Merge group event processed"
            update_check_run_mock.assert_awaited_once_with(
                "merge_group_sha", "canonical/lxd", installation_id=456
            )


class TestUpdateCheckRunHelpers:
    @pytest.mark.asyncio
    async def test_is_repo_excluded_true(
        self,
        service: GithubWebhookService,
        excluded_project_repository_mock,
    ):
        project = ExcludedProject(
            platform=ProjectPlatform.GITHUB, full_name="canonical/excluded-repo"
        )
        excluded_project_repository_mock.get_projects_excluded.return_value = [
            (project, True)
        ]

        result = await service._is_repo_excluded("canonical/excluded-repo")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_repo_excluded_false(
        self,
        service: GithubWebhookService,
        excluded_project_repository_mock,
    ):
        project = ExcludedProject(
            platform=ProjectPlatform.GITHUB, full_name="canonical/lxd"
        )
        excluded_project_repository_mock.get_projects_excluded.return_value = [
            (project, False)
        ]

        result = await service._is_repo_excluded("canonical/lxd")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_commit_authors(self, service: GithubWebhookService):
        g_mock = AsyncMock()
        repo_full_name = "canonical/lxd"
        pr_number = 1

        async def getitem_side_effect(url):
            if url == "commit_url_1":
                return {
                    "commit": {
                        "author": {"email": "author1@example.com"},
                        "message": "feat: new feature",
                    },
                    "author": {"login": "author1"},
                }
            if url == "commit_url_2":
                return {
                    "commit": {
                        "author": {"email": "author2@example.com"},
                        "message": "fix: a bug",
                    },
                    "author": {"login": "author2"},
                }
            return {}

        g_mock.getitem.side_effect = getitem_side_effect

        async def getiter_return(*args, **kwargs):
            yield {"url": "commit_url_1"}
            yield {"url": "commit_url_2"}

        g_mock.getiter = MagicMock(return_value=getiter_return())

        authors = await service._get_commit_authors(g_mock, repo_full_name, pr_number)

        assert authors == {
            "author1@example.com": {"username": "author1", "signed": False},
            "author2@example.com": {"username": "author2", "signed": False},
        }
        g_mock.getiter.assert_called_once_with("/repos/canonical/lxd/pulls/1/commits")

    @pytest.mark.asyncio
    async def test_get_commit_authors_implicit_license(
        self, service: GithubWebhookService
    ):
        g_mock = AsyncMock()
        repo_full_name = "canonical/lxd"  # This repo is in LICENSE_MAP
        pr_number = 1

        async def getitem_side_effect(url):
            if url == "commit_url_1":
                return {
                    "commit": {
                        "author": {"email": "author1@example.com"},
                        "message": "feat: new feature\n\nLicense: Apache-2.0",
                    },
                    "author": {"login": "author1"},
                }
            return {}

        g_mock.getitem.side_effect = getitem_side_effect

        async def getiter_return(*args, **kwargs):
            yield {"url": "commit_url_1"}

        g_mock.getiter = MagicMock(return_value=getiter_return())

        authors = await service._get_commit_authors(g_mock, repo_full_name, pr_number)

        assert authors == {}

    @pytest.mark.asyncio
    async def test_check_authors_cla(
        self, service: GithubWebhookService, cla_service_mock
    ):
        commit_authors = {
            "author1@example.com": {"username": "author1", "signed": False},
            "author2@example.com": {"username": "author2", "signed": False},
            "bot@example.com": {"username": "dependabot[bot]", "signed": False},
        }

        cla_service_mock.check_cla.return_value = MagicMock(
            emails={"author1@example.com": True},
            github_usernames={"author2": False},
        )

        result = await service._check_authors_cla(commit_authors)

        assert result["author1@example.com"]["signed"] is True
        assert result["author2@example.com"]["signed"] is False
        assert result["bot@example.com"]["signed"] is True
        cla_service_mock.check_cla.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_authors_cla_signed_by_github(
        self, service: GithubWebhookService, cla_service_mock
    ):
        commit_authors = {
            "author1@example.com": {"username": "author1", "signed": False},
        }

        cla_service_mock.check_cla.return_value = MagicMock(
            emails={"author1@example.com": False},
            github_usernames={"author1": True},
        )

        result = await service._check_authors_cla(commit_authors)

        assert result["author1@example.com"]["signed"] is True

    def test_create_check_run_output_all_signed(self, service: GithubWebhookService):
        authors = {
            "author1@example.com": {"username": "author1", "signed": True},
        }
        conclusion, output = service._create_check_run_output(authors)
        assert conclusion == "success"
        assert "All contributors have signed the CLA" in output["title"]
        assert "All contributors have signed the CLA. Thank you!" in output["summary"]
        assert "- author1 ✓ (CLA signed)" in output["summary"]

    def test_create_check_run_output_some_unsigned(self, service: GithubWebhookService):
        authors = {
            "author1@example.com": {"username": "author1", "signed": True},
            "author2@example.com": {"username": "author2", "signed": False},
        }
        conclusion, output = service._create_check_run_output(authors)
        assert conclusion == "failure"
        assert "CLA Check Failed" in output["title"]
        assert "Some commit authors have not signed" in output["summary"]
        assert "- author1 ✓ (CLA signed)" in output["summary"]
        assert "- author2 (author2@example.com) ✗ (CLA not signed)" in output["summary"]


@pytest.mark.asyncio
async def test_update_check_run(service: GithubWebhookService):
    with (
        patch.object(
            service, "_get_github_api_for_installation", new_callable=AsyncMock
        ) as get_api_mock,
        patch.object(
            service, "_is_repo_excluded", new_callable=AsyncMock, return_value=False
        ),
        patch.object(
            service, "_get_commit_authors", new_callable=AsyncMock
        ) as get_authors_mock,
        patch.object(
            service, "_check_authors_cla", new_callable=AsyncMock
        ) as check_cla_mock,
        patch.object(service, "_create_check_run_output") as create_output_mock,
        patch.object(
            service, "_update_or_create_check_run", new_callable=AsyncMock
        ) as update_run_mock,
    ):
        get_authors_mock.return_value = {
            "author1@example.com": {"username": "author1", "signed": False}
        }
        check_cla_mock.return_value = {
            "author1@example.com": {"username": "author1", "signed": True}
        }
        create_output_mock.return_value = (
            "success",
            {"title": "Success", "summary": "All signed"},
        )

        await service.update_check_run("test_sha", "canonical/lxd", 123, installation_id=456)

        get_api_mock.assert_awaited_once_with("canonical", 456)
        get_authors_mock.assert_awaited_once_with(
            get_api_mock.return_value, "canonical/lxd", 123
        )
        check_cla_mock.assert_awaited_once_with(get_authors_mock.return_value)
        create_output_mock.assert_called_once_with(check_cla_mock.return_value)
        update_run_mock.assert_awaited_once_with(
            get_api_mock.return_value,
            "canonical/lxd",
            "test_sha",
            "success",
            {"title": "Success", "summary": "All signed"},
        )


@pytest.mark.asyncio
async def test_update_check_run_excluded_repo(service: GithubWebhookService):
    with (
        patch.object(
            service, "_get_github_api_for_installation", new_callable=AsyncMock
        ) as get_api_mock,
        patch.object(
            service, "_is_repo_excluded", new_callable=AsyncMock, return_value=True
        ),
        patch.object(
            service, "_get_commit_authors", new_callable=AsyncMock
        ) as get_authors_mock,
        patch.object(
            service, "_update_or_create_check_run", new_callable=AsyncMock
        ) as update_run_mock,
    ):
        await service.update_check_run("test_sha", "canonical/excluded-repo", 123, installation_id=456)

        get_api_mock.assert_awaited_once_with("canonical", 456)
        get_authors_mock.assert_not_awaited()
        update_run_mock.assert_awaited_once_with(
            get_api_mock.return_value,
            "canonical/excluded-repo",
            "test_sha",
            "success",
            {
                "title": "CLA check not required",
                "summary": "The repository canonical/excluded-repo is excluded from CLA checks.",
            },
        )


@pytest.mark.asyncio
async def test_update_check_run_for_merge_group(service: GithubWebhookService):
    with (
        patch.object(
            service, "_get_github_api_for_installation", new_callable=AsyncMock
        ) as get_api_mock,
        patch.object(
            service, "_is_repo_excluded", new_callable=AsyncMock, return_value=False
        ),
        patch.object(
            service, "_get_merge_group_commit_authors", new_callable=AsyncMock
        ) as get_authors_mock,
        patch.object(
            service, "_check_authors_cla", new_callable=AsyncMock
        ) as check_cla_mock,
        patch.object(service, "_create_check_run_output") as create_output_mock,
        patch.object(
            service, "_update_or_create_check_run", new_callable=AsyncMock
        ) as update_run_mock,
    ):
        get_authors_mock.return_value = {
            "author1@example.com": {"username": "author1", "signed": False}
        }
        check_cla_mock.return_value = {
            "author1@example.com": {"username": "author1", "signed": True}
        }
        create_output_mock.return_value = (
            "success",
            {"title": "Success", "summary": "All signed"},
        )

        await service.update_check_run(
            "merge_sha", "canonical/lxd", installation_id=456
        )

        get_api_mock.assert_awaited_once_with("canonical", 456)
        get_authors_mock.assert_awaited_once_with(
            get_api_mock.return_value, "canonical/lxd", "merge_sha"
        )
        check_cla_mock.assert_awaited_once_with(get_authors_mock.return_value)
        create_output_mock.assert_called_once_with(check_cla_mock.return_value)
        update_run_mock.assert_awaited_once_with(
            get_api_mock.return_value,
            "canonical/lxd",
            "merge_sha",
            "success",
            {"title": "Success", "summary": "All signed"},
        )


@pytest.mark.asyncio
async def test_update_check_run_for_merge_group_excluded_repo(
    service: GithubWebhookService,
):
    with (
        patch.object(
            service, "_get_github_api_for_installation", new_callable=AsyncMock
        ) as get_api_mock,
        patch.object(
            service, "_is_repo_excluded", new_callable=AsyncMock, return_value=True
        ),
        patch.object(
            service, "_get_merge_group_commit_authors", new_callable=AsyncMock
        ) as get_authors_mock,
        patch.object(
            service, "_update_or_create_check_run", new_callable=AsyncMock
        ) as update_run_mock,
    ):
        await service.update_check_run(
            "merge_sha", "canonical/excluded-repo", installation_id=456
        )

        get_api_mock.assert_awaited_once_with("canonical", 456)
        get_authors_mock.assert_not_awaited()
        update_run_mock.assert_awaited_once_with(
            get_api_mock.return_value,
            "canonical/excluded-repo",
            "merge_sha",
            "success",
            {
                "title": "CLA check not required",
                "summary": "The repository canonical/excluded-repo is excluded from CLA checks.",
            },
        )


class TestGetMergeGroupCommitAuthors:
    @pytest.mark.asyncio
    async def test_merge_commit_with_parents(self, service: GithubWebhookService):
        """Test extracting authors from a merge group merge commit."""
        g_mock = AsyncMock()

        async def getitem_side_effect(url):
            if url == "/repos/canonical/lxd/commits/merge_sha":
                return {
                    "commit": {
                        "author": {"email": "github-merge-queue@users.noreply.github.com"},
                        "message": "Merge pull request",
                    },
                    "author": {"login": "github-merge-queue[bot]"},
                    "parents": [
                        {"url": "https://api.github.com/repos/canonical/lxd/commits/base_sha"},
                        {"url": "https://api.github.com/repos/canonical/lxd/commits/pr_head_sha"},
                    ],
                }
            if url == "https://api.github.com/repos/canonical/lxd/commits/pr_head_sha":
                return {
                    "commit": {
                        "author": {"email": "author1@example.com"},
                        "message": "feat: my feature",
                    },
                    "author": {"login": "author1"},
                }
            return {}

        g_mock.getitem.side_effect = getitem_side_effect

        authors = await service._get_merge_group_commit_authors(
            g_mock, "canonical/lxd", "merge_sha"
        )

        assert "github-merge-queue@users.noreply.github.com" in authors
        assert "author1@example.com" in authors
        assert authors["author1@example.com"] == {
            "username": "author1",
            "signed": False,
        }

    @pytest.mark.asyncio
    async def test_single_commit_no_parents(self, service: GithubWebhookService):
        """Test merge group with a single commit (no extra parents)."""
        g_mock = AsyncMock()

        async def getitem_side_effect(url):
            if url == "/repos/canonical/lxd/commits/single_sha":
                return {
                    "commit": {
                        "author": {"email": "author1@example.com"},
                        "message": "feat: my feature",
                    },
                    "author": {"login": "author1"},
                    "parents": [
                        {"url": "https://api.github.com/repos/canonical/lxd/commits/base_sha"},
                    ],
                }
            return {}

        g_mock.getitem.side_effect = getitem_side_effect

        authors = await service._get_merge_group_commit_authors(
            g_mock, "canonical/lxd", "single_sha"
        )

        assert authors == {
            "author1@example.com": {"username": "author1", "signed": False},
        }

    @pytest.mark.asyncio
    async def test_implicit_license_skipped(self, service: GithubWebhookService):
        """Test that commits with implicit licenses are skipped."""
        g_mock = AsyncMock()

        async def getitem_side_effect(url):
            if url == "/repos/canonical/lxd/commits/merge_sha":
                return {
                    "commit": {
                        "author": {"email": "author1@example.com"},
                        "message": "feat: my feature\n\nLicense: Apache-2.0",
                    },
                    "author": {"login": "author1"},
                    "parents": [],
                }
            return {}

        g_mock.getitem.side_effect = getitem_side_effect

        authors = await service._get_merge_group_commit_authors(
            g_mock, "canonical/lxd", "merge_sha"
        )

        assert authors == {}
