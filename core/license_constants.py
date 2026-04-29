"""
License system constants. PUBLIC_KEY_PEM must be filled in after running
tools/generate_keys.py. All other values are stable configuration.
"""

import sys
from pathlib import Path

# ── Public Key ────────────────────────────────────────────────────────────────
# Paste the full output of tools/generate_keys.py here (including header/footer).
# This value never changes unless you regenerate the key pair.
PUBLIC_KEY_PEM = """\
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAoI7pYGUqMndhR6x4lqWM
3NlOg7XrMM2PkFvYnv0v8pQkAxmQj0rp4tOfQ4mhd37eXo+EuRDgwm0wvJfcLEY2
WsrwkX7fPw4Jm2XPLuTkMteM/gfLTsG9dyYGxer0gxrEeTBpGYkjvXHI0V2K8BgE
W8/tNRHj9dROeEcB7JyQSlMkrI/NBUO9krmXemYCMMAzs2wwWuxXRVlMSOuiTrg2
9IUMQJ1jJC6D3z3VTDukN2cBSXmvula3fjQBehZ6gNn5Ypx6lTIgQHVVnhvQ4KkR
5V/WeLQN+vvEkdTOsPGjqJMrzyVmN8sZPSeiq8wHGpntsxNksS7e24PcuPQQsKKr
2QIDAQAB
-----END PUBLIC KEY-----
"""

# ── License file ──────────────────────────────────────────────────────────────
LICENSE_FILE_NAME = "cleansheet.lic"

_PROJECT_ROOT = Path(__file__).parent.parent

if getattr(sys, "frozen", False):
    # Running as a PyInstaller bundle
    LICENSE_SEARCH_PATHS: list[Path] = [
        Path(sys.executable).parent,
        Path("C:/ProgramData/CleanSheet"),
        Path.home(),
    ]
else:
    # Development
    LICENSE_SEARCH_PATHS: list[Path] = [
        _PROJECT_ROOT / "license",
    ]

# ── App version ───────────────────────────────────────────────────────────────
# Canonical definition lives in core/constants.py — imported here for backwards compat.
from core.constants import APP_VERSION as APP_VERSION  # noqa: F401
