# CleanSheet — License System Implementation

Full implementation guide for RSA-signed, machine-locked licensing. Read this document completely before writing any code. Each section is ordered by implementation sequence.

---

## Overview

The license system has three components:

- Key generator — run once by you to create your RSA key pair
- License generator — run by you each time you issue a license to a client
- License validator — embedded in the app, runs on every startup

No server required. No internet required at runtime. No database.

---

## Dependencies

Add to your requirements.txt:

```
cryptography>=42.0.0
```

This is the only new dependency. It bundles cleanly with PyInstaller.

---

## Part 1 — Key Generator

Run this script exactly once. Store the output files securely. Never add private_key.pem to git.

Script name: `tools/generate_keys.py`

This script does the following:

- Generates an RSA-2048 key pair
- Saves the private key to `private_key.pem` in the current directory
- Saves the public key to `public_key.pem` in the current directory
- Prints confirmation and reminds you to back up the private key

Implementation notes:

- Use `cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key` with `public_exponent=65537` and `key_size=2048`
- Serialize private key using `PKCS8` encoding, `PEM` format, `BestAvailableEncryption` with a passphrase you choose — this passphrase is required every time you generate a license
- Serialize public key using `SubjectPublicKeyInfo` encoding, `PEM` format, no encryption
- Print the public key content to terminal after generation — you will copy this into the app

After running:

- `private_key.pem` — keep on your machine only, back up to a USB drive, never commit to git
- `public_key.pem` — copy the contents into the app's constants file (see Part 3)
- Add `private_key.pem` and `private_key.pem.bak` to `.gitignore` immediately

---

## Part 2 — Machine ID Generation

This module runs inside the app. It reads hardware identifiers and produces a short, human-readable Machine ID.

Module name: `core/machine_id.py`

### Hardware identifiers to read

Read all three. If any one fails (hardware doesn't expose it, WMI error), use an empty string for that component — do not crash.

Identifier 1 — CPU ID:
- Read from Windows registry key: `HARDWARE\DESCRIPTION\System\CentralProcessor\0`, value `ProcessorNameString`
- Use `winreg` module (built into Python)
- Strip whitespace from the value

Identifier 2 — Motherboard serial:
- Read via `subprocess` running the command: `wmic baseboard get SerialNumber`
- Parse the output: split lines, strip whitespace, take the second non-empty line
- If output contains "To be filled" or is empty, use empty string

Identifier 3 — Windows Machine GUID:
- Read from registry key: `SOFTWARE\Microsoft\Cryptography`, value `MachineGuid`
- This GUID is assigned by Windows on installation and is stable

### Combining into Machine ID

- Concatenate the three values with a separator: `cpu_id + "|" + board_serial + "|" + machine_guid`
- Hash the combined string using `hashlib.sha256`
- Take the first 12 characters of the hex digest
- Format as groups of 4 separated by hyphens: `A3F9-22BC-91DE`
- Convert to uppercase

The resulting Machine ID is what the app displays on the activation screen and what you embed in the license file.

### Fallback behaviour

If all three reads fail (unusual, only on very locked-down systems):
- Use Python's `uuid.getnode()` as a fallback — this returns the MAC address as an integer
- Hash it the same way
- Log a warning that hardware identifiers were unavailable and fallback was used

---

## Part 3 — Public Key in App

The public key must be embedded in the app at build time, not loaded from an external file.

File: `core/license_constants.py`

Store the public key as a multi-line string constant. Copy the full contents of `public_key.pem` including the `-----BEGIN PUBLIC KEY-----` and `-----END PUBLIC KEY-----` header and footer lines.

Also define in this file:

- `LICENSE_FILE_NAME = "cleansheet.lic"`
- `LICENSE_SEARCH_PATHS` — a list of directories where the app will look for the license file:
  - Same directory as the executable (for development and portable use)
  - `C:\ProgramData\CleanSheet\` (standard install location)
  - User's home directory as a last fallback
- `APP_VERSION` — current version string

The public key string never changes unless you regenerate the key pair. Treat it like a constant, not configuration.

But for now since the installer is not implemented read licence file from this development folder, we will change paths when finally packaging. 
---

## Part 4 — License Generator

Run this script each time you issue or renew a license for a client. You run this on your own machine.

Script name: `tools/generate_license.py`

### Inputs

The script accepts these inputs (prompt for them interactively at the terminal):

- Client name — string, will be embedded in the license
- Machine ID — the A3F9-22BC-91DE style string the client sends you
- Expiry date — in YYYY-MM-DD format, e.g. 2026-12-31
- Path to private_key.pem
- Passphrase for the private key

### Data payload

Construct the payload string as:

```
ClientName|2026-12-31|A3F9-22BC-91DE
```

All three fields separated by pipe characters. No spaces around pipes.

### Signing

- Load the private key from file using the passphrase
- Sign the payload bytes using `PKCS1v15` padding and `SHA256` hash algorithm
- The result is a bytes object — encode it as base64 using `base64.b64encode`

### License file format

The `.lic` file contains two lines:

Line 1 — the payload string as plain text:
```
ClientName|2026-12-31|A3F9-22BC-91DE
```

Line 2 — the base64-encoded signature:
```
T3BlblNTSD1234abcd...
```

Save as `ClientName_cleansheet.lic`. The filename does not affect validation — only the contents matter.

### Output

Print to terminal:
- License file path
- Client name, expiry, machine ID (for your confirmation)
- A reminder to send the file by email

---

## Part 5 — License Validator

This is the core module embedded in the app. It runs on every startup.

Module name: `core/license_validator.py`

### Data structures

Define a result object (use a dataclass or a simple class) with these fields:

- `valid` — boolean
- `client_name` — string or None
- `expiry_date` — date object or None
- `failure_reason` — one of: `NO_FILE`, `INVALID_FORMAT`, `INVALID_SIGNATURE`, `EXPIRED`, `WRONG_MACHINE`
- `failure_message` — human-readable string for display to user

### Validation function

The main function `validate_license()` returns the result object. It performs checks in this exact order, returning immediately on first failure.

Step 1 — Find the license file:
- Search each path in `LICENSE_SEARCH_PATHS` in order
- If no file found anywhere: return `NO_FILE` with message "No license file found. Please contact support@gd365.com to activate CleanSheet."

Step 2 — Read and parse the file:
- Read all lines, strip whitespace
- Expect exactly 2 non-empty lines
- If not: return `INVALID_FORMAT` with message "License file is corrupted. Please contact support to receive a new license file."
- Line 1 is the payload, Line 2 is the base64 signature
- Split payload by `|` — expect exactly 3 parts
- If not: return `INVALID_FORMAT` with same message

Step 3 — Verify the signature:
- Decode the base64 signature bytes
- Load the public key from `LICENSE_CONSTANTS.PUBLIC_KEY_PEM`
- Call `public_key.verify(signature, payload_bytes, PKCS1v15(), SHA256())`
- This raises an `InvalidSignature` exception if it fails — catch it
- If signature invalid: return `INVALID_SIGNATURE` with message "License file is not valid. Please contact support."
- Do not tell the user specifically that the signature failed — just that it is not valid

Step 4 — Check expiry:
- Parse the date string from the payload (part index 1) as `YYYY-MM-DD`
- Compare to `datetime.date.today()`
- If today is after the expiry date: return `EXPIRED` with message "Your CleanSheet license expired on [date]. Please contact support@gd365.com to renew."
- Include the actual expiry date in the message

Step 5 — Check machine fingerprint:
- Call `get_machine_id()` from `core/machine_id.py`
- Compare to the machine ID embedded in the payload (part index 2)
- Case-insensitive comparison, strip whitespace
- If not matching: return `WRONG_MACHINE` with message "This license is not valid for this computer. If you have changed your hardware, please contact support@gd365.com with your new Machine ID."
- Do not reveal the expected or actual machine ID in the message

Step 6 — All checks passed:
- Set `valid = True`
- Parse and store `client_name` (part index 0) and `expiry_date`
- Return the result

### Additional helper

`get_days_until_expiry(result)` — takes a valid result and returns the number of days remaining. Use this to show a renewal warning when fewer than 14 days remain.

---

## Part 6 — Activation Screen

Shown when `validate_license()` returns `valid = False`.

Screen name: `ui/activation_screen.py`

### Layout

The screen is a standalone dialog or window — not part of the main app navigation. It appears before any other screen loads.

Show at top: CleanSheet logo and name.

Below that, show the failure reason with appropriate context:

For `NO_FILE` — show the activation flow:
- Heading: "Activate CleanSheet"
- Label: "Your Machine ID"
- Display box showing the Machine ID (monospace font, non-editable)
- Button: "Copy Machine ID" — copies to clipboard, button text changes to "Copied" for 2 seconds
- Instructions text: "Send your Machine ID to support@gd365.com. You will receive a license file by email."
- Divider
- Label: "Already have a license file?"
- Button: "Browse for License File" — opens file picker filtered to .lic files
- On file selected: copy it to the first writable path in LICENSE_SEARCH_PATHS, then re-run validation and either open the app or show the appropriate error

For `EXPIRED` — show:
- Heading: "License Expired"
- The failure message with the date
- Contact email, clickable to open mail client
- Button: "Browse for New License File" — same as above

For `WRONG_MACHINE` — show:
- Heading: "License Not Valid for This Computer"
- The failure message
- Show Machine ID with copy button (so they can send you the new one)
- Contact email

For `INVALID_SIGNATURE` or `INVALID_FORMAT` — show:
- Heading: "Invalid License File"
- The failure message
- Contact email
- Button: "Browse for License File" — in case they have a valid one elsewhere

### Startup integration

In your main application entry point, before creating or showing any main window:

- Call `validate_license()`
- If `result.valid` is False: show the activation screen, do not proceed
- If `result.valid` is True:
  - Store the result (client name, expiry) in a lightweight app-wide state object
  - If `get_days_until_expiry(result)` is less than 14: show a non-blocking banner or dialog warning of upcoming expiry after the main window loads
  - Proceed with normal app startup

---

## Part 7 — PyInstaller Configuration

The public key string is embedded in Python source and bundles automatically. No special handling needed for the key itself.

Add to your PyInstaller .spec file or command:

- `--collect-all cryptography` — ensures all cryptography backend files are bundled
- Alternatively add `cryptography` to `hiddenimports` in the spec file

After building, test the following on a machine that has never had Python installed:

- App launches and shows activation screen (no .lic file)
- Machine ID is generated and displayed (not blank, not an error)
- Placing a valid .lic file and restarting opens the app
- An expired .lic file shows the expired message
- A .lic file from a different machine shows the wrong machine message

---

## Part 8 — Operational Guide (Your Side)

### First setup

1. Run `generate_keys.py` once
2. Copy public key content into `license_constants.py`
3. Back up `private_key.pem` to a USB drive stored securely
4. Add `private_key.pem` to `.gitignore`
5. Build and ship the app — public key is now baked in

### Per-client activation

1. Client emails you their Machine ID
2. Run `generate_license.py`
3. Enter client name, machine ID, expiry date (typically today + 1 month or + 1 year)
4. Script outputs `ClientName_cleansheet.lic`
5. Email the file to the client
6. Client places it next to the exe or in `C:\ProgramData\CleanSheet\`
7. Client restarts app — it activates

### Monthly renewal

1. Client emails to renew (or you proactively send before expiry)
2. Run `generate_license.py` with the same machine ID, updated expiry date
3. Email new .lic file
4. Client replaces old file, restarts — done

### Hardware change

1. Client contacts you — they see "license not valid for this computer"
2. They send you their new Machine ID (from the activation screen)
3. Run `generate_license.py` with the new machine ID
4. Email new .lic file
5. Client activates on new machine — old machine can no longer use that license

### Key management rules

- Private key passphrase: store in a password manager, not written down anywhere
- If you lose the private key: all existing licenses still work (they validate against the baked-in public key), but you cannot generate new licenses — you must rebuild the app with a new key pair and re-issue all client licenses
- Never share the private key with anyone, including contractors

---

## File Structure Summary

```
your-project/
├── tools/
│   ├── generate_keys.py          (run once, outputs key files)
│   └── generate_license.py       (run per client)
├── core/
│   ├── license_constants.py      (public key + config)
│   ├── machine_id.py             (hardware fingerprint)
│   └── license_validator.py      (validation logic)
├── ui/
│   └── activation_screen.py      (shown when not activated)
├── private_key.pem               (NEVER commit — add to .gitignore)
└── public_key.pem                (safe to commit, already in constants)
```

---

## Testing Checklist

Before shipping to any client, verify all of these locally:

- [ ] `generate_keys.py` runs without error, produces both key files
- [ ] `generate_license.py` runs, produces a .lic file
- [ ] App with no .lic file shows activation screen
- [ ] Machine ID is displayed and non-empty
- [ ] Copy button works
- [ ] Valid .lic placed next to exe: app opens
- [ ] Expiry date in the past: shows expired message with correct date
- [ ] Machine ID in .lic changed by one character: shows wrong machine message
- [ ] Signature modified in .lic: shows invalid license message
- [ ] .lic file is empty or has one line: shows corrupted message
- [ ] 14 days before expiry: renewal warning shown after main window loads
- [ ] All of the above tested on a machine without Python installed
