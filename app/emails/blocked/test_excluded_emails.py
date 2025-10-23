import pytest

from app.emails.blocked.excluded_emails import EXCLUDED_EMAILS, excluded_email


@pytest.mark.parametrize("domain", sorted(EXCLUDED_EMAILS))
def test_excluded_email_true_for_excluded_domains(domain):
    assert excluded_email(f"user@{domain}") is True
    assert excluded_email(f"USER@{domain.upper()}") is True
    assert excluded_email(f" user@{domain} ") is True


@pytest.mark.parametrize(
    "email",
    [
        "user@example.com",
        "user@intel.co",  # similar but different TLD
        "user@sub.intel.com",  # subdomain should not match unless listed
        "notanemail",
        "user@linuxintell.com",
    ],
)
def test_excluded_email_false_for_non_excluded_domains(email):
    assert excluded_email(email) is False
