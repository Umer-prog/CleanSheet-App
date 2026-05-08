"""
License validator. Call validate_license() on every app startup.
Returns a LicenseResult immediately — no network, no database.
"""

from __future__ import annotations

import base64
import datetime
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from core.license_constants import LICENSE_FILE_NAME, LICENSE_SEARCH_PATHS, PUBLIC_KEY_PEM
from core.machine_id import get_machine_id

logger = logging.getLogger(__name__)

_FAILURE_REASONS = frozenset([
    "NO_FILE", "INVALID_FORMAT", "INVALID_SIGNATURE", "EXPIRED", "WRONG_MACHINE",
])


@dataclass
class LicenseResult:
    valid: bool = False
    client_name: Optional[str] = None
    expiry_date: Optional[datetime.date] = None
    failure_reason: Optional[str] = None
    failure_message: str = ""


def _find_license_file() -> Optional[Path]:
    for directory in LICENSE_SEARCH_PATHS:
        candidate = Path(directory) / LICENSE_FILE_NAME
        if candidate.exists():
            return candidate
    return None


def _load_public_key():
    return serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode())


def validate_license() -> LicenseResult:
    """Validate the license file. Checks are run in order; returns on first failure."""

    # Step 1 — find file
    lic_path = _find_license_file()
    if lic_path is None:
        return LicenseResult(
            failure_reason="NO_FILE",
            failure_message=(
                "No license file found. Please contact support@globaldata365.com to activate BI CleanSheet 365."
            ),
        )

    # Step 2 — read and parse
    try:
        lines = [ln.strip() for ln in lic_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError:
        lines = []

    if len(lines) != 2:
        return LicenseResult(
            failure_reason="INVALID_FORMAT",
            failure_message="License file is corrupted. Please contact support to receive a new license file.",
        )

    payload_str, sig_b64 = lines[0], lines[1]
    parts = payload_str.split("|")
    if len(parts) != 3:
        return LicenseResult(
            failure_reason="INVALID_FORMAT",
            failure_message="License file is corrupted. Please contact support to receive a new license file.",
        )

    client_name, expiry_str, machine_id_in_lic = parts

    # Step 3 — verify signature
    try:
        sig_bytes = base64.b64decode(sig_b64)
        public_key = _load_public_key()
        public_key.verify(sig_bytes, payload_str.encode(), padding.PKCS1v15(), hashes.SHA256())
    except InvalidSignature:
        return LicenseResult(
            failure_reason="INVALID_SIGNATURE",
            failure_message="License file is not valid. Please contact support.",
        )
    except Exception as exc:
        logger.warning("Public key load / verify error: %s", exc)
        return LicenseResult(
            failure_reason="INVALID_SIGNATURE",
            failure_message="License file is not valid. Please contact support.",
        )

    # Step 4 — check expiry
    try:
        expiry_date = datetime.datetime.strptime(expiry_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return LicenseResult(
            failure_reason="INVALID_FORMAT",
            failure_message="License file is corrupted. Please contact support to receive a new license file.",
        )

    if datetime.date.today() > expiry_date:
        return LicenseResult(
            failure_reason="EXPIRED",
            failure_message=(
                f"Your BI CleanSheet 365 license expired on {expiry_date.strftime('%d %B %Y')}. "
                "Please contact support@globaldata365.com to renew."
            ),
        )

    # Step 5 — check machine fingerprint
    current_machine_id = get_machine_id()
    if current_machine_id.strip().upper() != machine_id_in_lic.strip().upper():
        return LicenseResult(
            failure_reason="WRONG_MACHINE",
            failure_message=(
                "This license is not valid for this computer. "
                "If you have changed your hardware, please contact support@globaldata365.com "
                "with your new Machine ID."
            ),
        )

    # Step 6 — all checks passed
    return LicenseResult(
        valid=True,
        client_name=client_name,
        expiry_date=expiry_date,
    )


def get_days_until_expiry(result: LicenseResult) -> int:
    """Return days remaining on a valid license. Only meaningful when result.valid is True."""
    if result.expiry_date is None:
        return 0
    return (result.expiry_date - datetime.date.today()).days
