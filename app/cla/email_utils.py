import validators

from app.cla.email_providers import EMAIL_PROVIDERS


def clean_email_domain(domain: str):
    """
    Clean the email domain by removing any leading/trailing spaces and converting it to lowercase.
    """
    return domain.strip().lower()


def clean_email(email: str):
    """
    Clean the email by removing any leading/trailing spaces and converting it to lowercase.
    """
    return email.strip().lower()


def email_domain(email: str):
    """
    Extract the domain from the email.
    """
    return clean_email_domain(email.split("@")[-1])


def valid_email_domain(domain: str) -> (bool, str):
    """
    Checks if the email domain is valid and not a known email provider.
    """
    is_valid = validators.domain(domain, consider_tld=True)
    if not is_valid:
        return False, "Invalid email domain"

    # make sure the domain is not a known email provider
    if domain in EMAIL_PROVIDERS:
        return (
            False,
            "An email provider domain name cannot be used as an organization email domain",
        )
    return True, "Valid email domain"


def valid_email(email: str) -> bool:
    """
    Checks if the email format is valid.
    """
    return validators.email(email)
