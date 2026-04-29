"""
Run once to generate the RSA-2048 key pair.
Outputs keys/private_key.pem and keys/public_key.pem inside the project root.

IMPORTANT:
  - Back up keys/private_key.pem to a USB drive immediately after running.
  - Never commit private_key.pem to git.
  - Copy the printed public key into core/license_constants.py.
"""

from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Always write relative to this script's parent (tools/) → one level up = project root
_KEYS_DIR = Path(__file__).parent.parent / "keys"


def main() -> None:
    passphrase = input("Enter a passphrase to encrypt the private key: ").encode()
    if not passphrase:
        print("Passphrase cannot be empty. Aborting.")
        return

    confirm = input("Confirm passphrase: ").encode()
    if passphrase != confirm:
        print("Passphrases do not match. Aborting.")
        return

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(passphrase),
    )

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    _KEYS_DIR.mkdir(exist_ok=True)
    private_path = _KEYS_DIR / "private_key.pem"
    public_path  = _KEYS_DIR / "public_key.pem"

    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)

    print("\n--- PUBLIC KEY (copy into core/license_constants.py) ---")
    print(public_pem.decode())
    print("--- END PUBLIC KEY ---\n")
    print(f"private_key.pem -> {private_path.resolve()}")
    print(f"public_key.pem  -> {public_path.resolve()}")
    print("\nACTION REQUIRED:")
    print("  1. Copy the public key above into core/license_constants.py")
    print("  2. Back up keys/private_key.pem to a USB drive")
    print("  3. Verify keys/private_key.pem is in .gitignore before committing")


if __name__ == "__main__":
    main()
