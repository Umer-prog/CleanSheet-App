"""
Hardware fingerprint module. Reads three stable Windows identifiers,
hashes them, and returns a short human-readable Machine ID like A3F9-22BC-91DE.
"""

import hashlib
import logging
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
    # Read via registry instead of wmic — no subprocess, no console flash,
    # works on Windows 11 24H2 where wmic was removed.
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\SystemInformation",
        )
        value, _ = winreg.QueryValueEx(key, "BIOSVersion")
        winreg.CloseKey(key)
        serial = value.strip()
        if "To be filled" in serial or not serial:
            return ""
        return serial
    except Exception:
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
