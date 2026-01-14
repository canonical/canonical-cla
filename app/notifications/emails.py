import logging
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from smtplib import SMTP
from typing import Literal

import bleach
import jinja2
import pycountry

from app.config import config

logger = logging.getLogger(__name__)
templates_loader = jinja2.FileSystemLoader(Path(__file__).parent / "templates")
templates = jinja2.Environment(loader=templates_loader)


def send_email(email: str, subject: str, body: str) -> None:
    """
    Send an email to the provided email address.
    raises: SMTPException if the email could not be sent.
    """
    logger.info(f"Sending email ({subject}) to {email}")
    message = MIMEText(body, "html", "utf-8")
    message["From"] = config.smtp.from_email
    message["Reply-To"] = config.smtp.community_contact_email
    message["To"] = email
    message["Subject"] = subject
    smtp = SMTP(host=config.smtp.host, port=config.smtp.port)
    is_local = config.smtp.host == "localhost" or config.smtp.host == "127.0.0.1"
    if not is_local:
        smtp.starttls()
    smtp.login(config.smtp.username, config.smtp.password.get_secret_value())
    smtp.send_message(message)
    smtp.quit()
    logger.info(f"Email ({subject}) has been sent to {email}")


def sanitize_context(context):
    santized_context = {}
    for k, v in context.items():
        if isinstance(v, str):
            santized_context[k] = bleach.clean(v)
        else:
            santized_context[k] = v
    return santized_context


def send_individual_confirmation_email(email: str, name: str) -> None:
    """
    Send an email to the individual contributor confirming the signing of the CLA.
    """
    subject = "Canonical CLA Signed"

    send_email(
        formataddr((name, email)),
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


def send_organization_confirmation_email(
    email: str, name: str, organization_name: str, email_domain
) -> None:
    """
    Send an email to the organization confirming the signing of the CLA.
    """
    subject = "Canonical CLA Signed"
    send_email(
        formataddr((name, email)),
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


def send_legal_notification(
    organization_name: str,
    contact_name: str,
    contact_email: str,
    phone_number: str | None,
    contact_job_title: str,
    address: str | None,
    country: str,
    email_domain: str,
    cla_management_url: str,
):
    """
    Send an email to the community team notifying them of a new organization signing the CLA.
    """
    subject = "Canonical CLA Signed - Action Required"

    send_email(
        config.smtp.community_contact_email,
        subject,
        body=templates.get_template(
            "cla_signed_community_notification.j2",
        ).render(
            sanitize_context(
                {
                    "organization_name": organization_name,
                    "contact_name": contact_name,
                    "contact_email": contact_email,
                    "contact_job_title": contact_job_title,
                    "phone_number": phone_number,
                    "address": address,
                    "country": pycountry.countries.get(alpha_2=country).name,
                    "email_domain": email_domain,
                    "cla_management_url": cla_management_url,
                }
            )
        ),
    )


Status = Literal["approved", "disabled"]


def send_organization_status_update(
    contact_email: str,
    contact_name: str,
    organization_name: str,
    status: Status,
    email_domain: str,
) -> None:
    """
    Send an email to the organization notifying them of their status update.
    """
    subject = f"Canonical CLA Status Update: {status.capitalize()}"
    send_email(
        formataddr((contact_name, contact_email)),
        subject,
        body=templates.get_template(
            "cla_org_status_update.j2",
        ).render(
            sanitize_context(
                {
                    "contact_name": contact_name,
                    "organization_name": organization_name,
                    "status": status,
                    "email_domain": email_domain,
                }
            )
        ),
    )


def send_organization_deleted(
    contact_email: str,
    contact_name: str,
    organization_name: str,
) -> None:
    """
    Send an email to the organization notifying them of their deletion.
    """
    subject = "Canonical CLA: Organization Request Rejected"
    send_email(
        formataddr((contact_name, contact_email)),
        subject,
        body=templates.get_template(
            "cla_org_deleted.j2",
        ).render(
            sanitize_context(
                {
                    "contact_name": contact_name,
                    "organization_name": organization_name,
                }
            )
        ),
    )
