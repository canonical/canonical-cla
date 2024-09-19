from app.cla.email_utils import email_domain

EXCLUDED_EMAILS = {"users.noreply.github.com"}


def excluded_email(email: str) -> bool:
    return email_domain(email) in EXCLUDED_EMAILS
