import logging
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

import aiosmtplib
import bleach
import jinja2
import pycountry

from app.config import config

logger = logging.getLogger(__name__)
templates_loader = jinja2.FileSystemLoader(Path(__file__).parent / "templates")
templates = jinja2.Environment(loader=templates_loader)


async def send_email(name: str, email: str, subject: str, body: str) -> None:
    """
    Send an email to the provided email address.
    raises: SMTPException if the email could not be sent.
    """
    message = MIMEText(body, "html", "utf-8")
    message["From"] = config.smtp.from_email
    message["To"] = formataddr((name, email))
    message["Subject"] = subject
    async with aiosmtplib.SMTP(
        hostname=config.smtp.host, port=config.smtp.port
    ) as smtp:
        await smtp.login(config.smtp.username, config.smtp.password.get_secret_value())
        await smtp.send_message(message)
        logger.info(f"Email ({subject}) has been sent to {email}")


def sanitize_context(context):
    santized_context = {}
    for k, v in context.items():
        if isinstance(v, str):
            santized_context[k] = bleach.clean(v)
        else:
            santized_context[k] = v
    return santized_context


async def send_individual_confirmation_email(email: str, name: str) -> None:
    """
    Send an email to the individual contributor confirming the signing of the CLA.
    """
    subject = "Canonical CLA Signed"

    await send_email(
        name,
        email,
        subject,
        body=templates.get_template(
            "cla_signed_confirmation.j2",
        ).render(
            sanitize_context(
                {
                    "contributor_name": name,
                    "is_organization": False,
                }
            )
        ),
    )


async def send_organization_confirmation_email(
    email: str, name: str, organization_name: str, email_domain
) -> None:
    """
    Send an email to the organization confirming the signing of the CLA.
    """
    subject = "Canonical CLA Signed"
    await send_email(
        name,
        email,
        subject,
        body=templates.get_template(
            "cla_signed_confirmation.j2",
        ).render(
            sanitize_context(
                {
                    "contributor_name": name,
                    "organization_name": organization_name,
                    "is_organization": True,
                    "email_domain": email_domain,
                }
            )
        ),
    )


async def send_legal_notification(
    organization_name: str,
    contact_name: str,
    contact_email: str,
    phone_number: str,
    address: str,
    country: str,
    email_domain: str,
    cla_management_url: str,
):
    """
    Send an email to the legal team notifying them of a new organization signing the CLA.
    """
    subject = "Canonical CLA Signed - Action Required"

    await send_email(
        "Canonical Legal Team",
        config.smtp.legal_contact_email,
        subject,
        body=templates.get_template(
            "cla_signed_legal_notification.j2",
        ).render(
            {
                "organization_name": organization_name,
                "contact_name": contact_name,
                "contact_email": contact_email,
                "phone_number": phone_number,
                "address": address,
                "country": pycountry.countries.get(alpha_2=country).name,
                "email_domain": email_domain,
                "cla_management_url": cla_management_url,
            }
        ),
    )
