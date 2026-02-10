# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly. **Do not open a public GitHub issue.**

### How to Report

1. **Preferred:** Use [GitHub Security Advisories](https://github.com/LioChanDaYo/RGPDpseudonymizer/security/advisories/new) (private)
2. **Alternative:** Contact the maintainer via [GitHub profile](https://github.com/LioChanDaYo)

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgement:** Within 72 hours
- **Assessment:** Within 1 week
- **Fix timeline:** Depends on severity; critical issues prioritized

## Security Model

GDPR Pseudonymizer is designed with privacy and security as core principles:

- **Local-only processing:** All data stays on the user's machine. No network calls, no telemetry, no cloud services.
- **Encryption:** Mapping tables are encrypted using AES-256-SIV (RFC 5297) with passphrase-derived keys (PBKDF2, 210K iterations).
- **No sensitive data in logs:** Structured logging via `structlog` is configured to never log entity values, names, or document content.
- **Dependency management:** Dependencies are locked via `poetry.lock` for reproducible, auditable builds.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |
| < 1.0   | No        |
