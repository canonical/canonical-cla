from app.emails.email_utils import email_domain

# email domains that are not allowed to sign the CLA
# users with emails matching these domains will be notified with a message
# to let them know that they are not allowed to sign the CLA.
BLOCKED_EMAIL_DOMAINS = {
    "intel.com",
    "linux.intel.com",
    "habana.ai",
}


def is_email_blocked(email: str) -> bool:
    return email_domain(email) in BLOCKED_EMAIL_DOMAINS
