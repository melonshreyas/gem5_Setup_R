#!/usr/bin/env python3
"""Email delivery for model-release HTML reports."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Optional, Sequence

_EMAIL_HELPER_PATH = Path(__file__).resolve().parents[1] / "SMOKE" / "send_email_report.py"
_EMAIL_SPEC = importlib.util.spec_from_file_location("model_release_smtp_helper", _EMAIL_HELPER_PATH)
if _EMAIL_SPEC is None or _EMAIL_SPEC.loader is None:
    raise ImportError(f"Unable to load email helper: {_EMAIL_HELPER_PATH}")
_EMAIL_MODULE = importlib.util.module_from_spec(_EMAIL_SPEC)
_EMAIL_SPEC.loader.exec_module(_EMAIL_MODULE)


def send_release_report_email(
    report_path: Path,
    recipients: Optional[Sequence[str]] = None,
    smtp_server: Optional[str] = None,
    smtp_port: int = 587,
    sender_email: Optional[str] = None,
    sender_password: Optional[str] = None,
    subject: str = "gem5 Model Release Report",
) -> bool:
    """Send one release-version HTML report as an email attachment."""
    return bool(
        _EMAIL_MODULE.send_history_report_email(
            html_report_path=report_path,
            to_addresses=recipients,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            sender_email=sender_email,
            sender_password=sender_password,
            subject=subject,
        )
    )
