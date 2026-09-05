#!/usr/bin/env python3
"""Send the generated smoke history HTML report by email as an attachment."""

from __future__ import annotations

import argparse
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, Sequence


def _normalize_recipients(recipients: Optional[Sequence[str] | str]) -> list[str]:
    """Normalize recipient values from CLI arguments or environment variables.
    This turns a list, comma-separated string, or empty input into a clean recipient list.
    """
    if recipients is None:
        return []
    if isinstance(recipients, str):
        raw_values = recipients.split(",")
    else:
        raw_values = list(recipients)

    normalized: list[str] = []
    for item in raw_values:
        value = str(item).strip()
        if value:
            normalized.append(value)
    return normalized


def send_history_report_email(
    html_report_path: Path,
    to_addresses: Optional[Sequence[str] | str] = None,
    smtp_server: Optional[str] = None,
    smtp_port: int = 587,
    sender_email: Optional[str] = None,
    sender_password: Optional[str] = None,
    subject: str = "gem5 Smoke Report",
) -> bool:
    """Send the HTML report as an email attachment.
    It builds an email message and attempts to deliver it through SMTP.
    """
    report_path = Path(html_report_path).expanduser().resolve()
    if not report_path.exists():
        raise FileNotFoundError(f"Report file was not found: {report_path}")

    recipients = _normalize_recipients(to_addresses)
    if not recipients:
        env_recipients = os.getenv("SMTP_RECIPIENTS")
        recipients = _normalize_recipients(env_recipients)
    if not recipients:
        recipients = ["shreyassbagi@gmail.com"]

    smtp_server = smtp_server or os.getenv("SMTP_SERVER") or "smtp.gmail.com"
    sender_email = sender_email or os.getenv("SENDER_EMAIL") or "shreyassbagi@gmail.com"
    sender_password = sender_password or os.getenv("SENDER_PASSWORD")

    if not recipients or not smtp_server:
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender_email or "smoke-report@example.com"
    message["To"] = ", ".join(recipients)
    message.set_content("See the attached gem5 smoke history report.")
    message.add_attachment(
        report_path.read_bytes(),
        maintype="text",
        subtype="html",
        filename=report_path.name,
    )

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        if sender_email and sender_password:
            server.login(sender_email, sender_password)
        server.send_message(message)
        server.quit()
    except Exception:
        return False

    return True


def parse_args() -> argparse.Namespace:
    """Parse the CLI options for the email helper.
    This makes the SMTP target, credentials, and recipients configurable from the shell.
    """
    parser = argparse.ArgumentParser(description="Send a generated smoketest HTML report by email.")
    parser.add_argument(
        "report_path",
        nargs="?",
        default="jenkins_history_asan_results.html",
        help="Path to the HTML report to send. Default: %(default)s",
    )
    parser.add_argument("--smtp-server", default=None, help="SMTP server hostname.")
    parser.add_argument("--smtp-port", type=int, default=587, help="SMTP server port.")
    parser.add_argument("--sender-email", default=None, help="Sender email address.")
    parser.add_argument("--sender-password", default=None, help="Sender password or app password.")
    parser.add_argument(
        "--recipient-email",
        action="append",
        default=None,
        help="Recipient email address. Repeat the flag for multiple recipients.",
    )
    parser.add_argument("--subject", default="gem5 Smoke Report", help="Email subject.")
    return parser.parse_args()


def main() -> int:
    """Run the email helper from the command line.
    It parses the arguments and sends the requested report if the SMTP settings work.
    """
    args = parse_args()
    success = send_history_report_email(
        html_report_path=Path(args.report_path),
        to_addresses=args.recipient_email or ["shreyassbagi@gmail.com"],
        smtp_server=args.smtp_server,
        smtp_port=args.smtp_port,
        sender_email=args.sender_email,
        sender_password=args.sender_password,
        subject=args.subject,
    )
    if success:
        print(f"Email sent successfully for {args.report_path}")
        return 0

    print(f"Email delivery failed for {args.report_path}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
