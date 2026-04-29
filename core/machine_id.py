"""
Hardware fingerprint module. Reads three stable Windows identifiers,
hashes them, and returns a short human-readable Machine ID like A3F9-22BC-91DE.
"""

import hashlib
import logging
import subprocess
import uuid
import winreg
from typing import Optional

logger = logging.getLogger(__name__)


def _read_cpu_id() -> str:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        )
        value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        winreg.CloseKey(key)
        return value.strip()
    except Exception:
        return ""


def _read_board_serial() -> str:
    try:
        result = subprocess.run(
            ["wmic", "baseboard", "get", "SerialNumber"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
        # lines[0] is the header "SerialNumber", lines[1] is the value
        if len(lines) >= 2:
            serial = lines[1]
            if "To be filled" in serial or not serial:
                return ""
            return serial
    except Exception:
        pass
    return ""


def _read_machine_guid() -> str:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        )
        value, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        return value.strip()
    except Exception:
        return ""


def _format_hash(hex_digest: str) -> str:
    chunk = hex_digest[:12].upper()
    return f"{chunk[0:4]}-{chunk[4:8]}-{chunk[8:12]}"


def get_machine_id() -> str:
    cpu = _read_cpu_id()
    board = _read_board_serial()
    guid = _read_machine_guid()

    combined = f"{cpu}|{board}|{guid}"

    if not any([cpu, board, guid]):
        logger.warning("All hardware identifiers unavailable; using MAC address fallback.")
        mac = str(uuid.getnode())
        combined = mac

    digest = hashlib.sha256(combined.encode()).hexdigest()
    return _format_hash(digest)
