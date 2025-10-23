from app.emails.email_utils import email_domain

# email domains that are not allowed to sign the CLA
# emails matching these domains will be hidden from the CLA sign page
EXCLUDED_EMAILS = {"users.noreply.github.com"}


def excluded_email(email: str) -> bool:
    return email_domain(email) in EXCLUDED_EMAILS
