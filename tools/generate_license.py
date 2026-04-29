"""
Run per client to issue or renew a CleanSheet license.
Prompts for client name, machine ID, expiry date, and private key details,
then writes a signed .lic file to the current directory.
"""

import base64
import sys
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def _load_private_key(key_path: Path, passphrase: bytes):
    with open(key_path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=passphrase)


def _prompt(label: str, required: bool = True) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value or not required:
            return value
        print(f"  {label} cannot be empty.")


def main() -> None:
    print("=== CleanSheet License Generator ===\n")

    client_name = _prompt("Client name")

    machine_id = _prompt("Machine ID (e.g. A3F9-22BC-91DE)")

    expiry_str = _prompt("Expiry date (YYYY-MM-DD)")
    try:
        expiry_str = datetime.strptime(expiry_str.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD. Aborting.")
        sys.exit(1)

    key_path_str = _prompt("Path to private_key.pem (e.g. keys/private_key.pem)")
    key_path = Path(key_path_str)
    if not key_path.exists():
        print(f"File not found: {key_path}. Aborting.")
        sys.exit(1)

    import getpass
    passphrase = getpass.getpass("Private key passphrase: ").encode()

    try:
        private_key = _load_private_key(key_path, passphrase)
    except Exception as exc:
        print(f"Failed to load private key: {exc}")
        sys.exit(1)

    payload = f"{client_name}|{expiry_str}|{machine_id}"
    payload_bytes = payload.encode()

    signature_bytes = private_key.sign(
        payload_bytes,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    signature_b64 = base64.b64encode(signature_bytes).decode()

    safe_name = client_name.replace(" ", "_")
    lic_filename = f"{safe_name}_cleansheet.lic"
    lic_path = Path(lic_filename)

    lic_path.write_text(f"{payload}\n{signature_b64}\n", encoding="utf-8")

    print(f"\nLicense file: {lic_path.resolve()}")
    print(f"  Client  : {client_name}")
    print(f"  Expiry  : {expiry_str}")
    print(f"  Machine : {machine_id}")
    print("\nRemember to send the .lic file to the client by email.")


if __name__ == "__main__":
    main()
