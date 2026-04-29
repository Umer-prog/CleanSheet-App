# CleanSheet — License Operational Guide

This guide is for the person issuing and managing CleanSheet licenses (you, the developer).
Clients never need to read this.

---

## First-Time Setup

Do this once before shipping to any client.

1. Run the key generator from the project root:
   ```
   py -3.12 tools/generate_keys.py
   ```
2. Enter a strong passphrase when prompted. Store it in your password manager — you need it every time you generate a license.
3. Copy the printed public key (including the `-----BEGIN PUBLIC KEY-----` and `-----END PUBLIC KEY-----` lines) into `core/license_constants.py`, replacing the placeholder.
4. Back up `keys/private_key.pem` to a USB drive stored securely. If you lose this file you cannot generate new licenses.
5. Confirm `keys/private_key.pem` is listed in `.gitignore` before committing anything.
6. Build and ship the app — the public key is now baked into the executable.

---

## Activating a New Client

1. Client installs and opens CleanSheet. The activation screen appears showing their **Machine ID** (format: `A3F9-22BC-91DE`).
2. Client copies their Machine ID and emails it to you.
3. Run the license generator:
   ```
   py -3.12 tools/generate_license.py
   ```
   Enter:
   - **Client name** — e.g. `Acme Corp`
   - **Machine ID** — paste what the client sent
   - **Expiry date** — e.g. `2027-01-31` (use zero-padded month/day)
   - **Path to private key** — `keys/private_key.pem`
   - **Passphrase** — your key passphrase

4. The script outputs a file like `Acme_Corp_cleansheet.lic` in the current folder.
5. Email the `.lic` file to the client.
6. Client opens CleanSheet → clicks **Browse for License File** → selects the `.lic` file → app activates.

---

## Renewing a License

1. Client emails you to renew (or you proactively reach out before the expiry date).
2. Run `tools/generate_license.py` with the **same Machine ID**, updated expiry date.
3. Email the new `.lic` file to the client.
4. Client opens CleanSheet → activation screen shows (license expired) → clicks **Browse for New License File** → selects the new file → app opens.

No need to reinstall the app.

---

## Hardware Change (Client Gets a New PC)

1. Client contacts you — they see "License not valid for this computer."
2. The activation screen shows their new Machine ID with a Copy button.
3. Client sends you the new Machine ID.
4. Run `tools/generate_license.py` with the new Machine ID and a fresh expiry date.
5. Email the new `.lic` file.
6. Client activates on the new machine. The old machine can no longer use that license.

---

## Key Management Rules

| Rule | Reason |
|---|---|
| Store the private key passphrase in a password manager only | Written-down passphrases get lost or found |
| Keep one USB backup of `keys/private_key.pem` off-site | If your machine dies, you can still issue licenses |
| Never share the private key with anyone | Whoever has it can generate unlimited licenses |
| Never commit `keys/private_key.pem` to git | Git history is permanent — even a deleted file can be recovered |

**If you lose the private key:** existing client licenses still work (they validate against the public key baked into the exe). But you cannot generate new licenses. You would need to regenerate the key pair, rebuild the app, and re-issue all client licenses.

---

## File Locations Reference

| File | Location | Purpose |
|---|---|---|
| `keys/private_key.pem` | Your machine only | Signs license files — never share |
| `keys/public_key.pem` | Project repo | Baked into the app at build time |
| `license/cleansheet.lic` | Development machine | Your own dev/test license |
| `C:/ProgramData/CleanSheet/cleansheet.lic` | Client machine | Standard install location |
| Next to `CleanSheet.exe` | Client machine | Portable / side-by-side location |

---

## Testing Checklist Before Shipping

- [ ] App with no `.lic` file shows activation screen
- [ ] Machine ID is displayed and non-empty
- [ ] Copy Machine ID button works
- [ ] Valid `.lic` placed via Browse: app opens normally
- [ ] Expired `.lic`: shows expiry message with correct date
- [ ] `.lic` from a different machine: shows wrong machine message
- [ ] Signature modified in `.lic`: shows invalid license message
- [ ] Empty or one-line `.lic`: shows corrupted message
- [ ] 14 days before expiry: renewal warning shown after main window loads
- [ ] All of the above tested on a machine without Python installed
