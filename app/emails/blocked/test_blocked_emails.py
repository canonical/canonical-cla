import pytest

from app.emails.blocked.blocked_emails import BLOCKED_EMAIL_DOMAINS, is_email_blocked


@pytest.mark.parametrize("domain", sorted(BLOCKED_EMAIL_DOMAINS))
def test_is_email_blocked_true_for_blocked_domains(domain):
    assert is_email_blocked(f"user@{domain}") is True
    assert is_email_blocked(f"USER@{domain.upper()}") is True
    assert is_email_blocked(f" user@{domain} ") is True


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
def test_is_email_blocked_false_for_non_blocked_domains(email):
    assert is_email_blocked(email) is False
