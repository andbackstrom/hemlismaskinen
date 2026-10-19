# Source snapshot and verification

Prepared for external review on 2026-10-19 (Europe/Stockholm).

This repository imports `server.py`, `index.html`, `compose.yaml`, and the existing tests from the workspace used to deploy HEMLISMASKINEN. Application files are copied without functional changes. Review documentation and CI are new; they do not modify the running service. No automatic deployment is configured.

## Application checksums

| File | SHA-256 |
| --- | --- |
| `server.py` | `569cbdc562d6b080623e64658ef91885aba00b57b704fd0eaf3bc0358fa71270` |
| `index.html` | `5c16cb7d3a4e99e8ce535401ded074e0b65a4d611fc7240a7129e9d8c139e4b0` |
| `compose.yaml` | `16894f6af46bad0a5963724ebd8eef8648c845af0fe1e88cd1e94481142a5a79` |

The HTML returned by the live service over HTTPS was fetched and its SHA-256 matched `index.html` above. A fresh attempt to read the NAS backend/configuration checksums was blocked by expired sudo authorization. Consequently, backend and container configuration provenance is the original deployment workspace, not an independently reconfirmed on-host hash. Do not treat this snapshot as a fresh attestation of every running backend or infrastructure setting.

## Verification performed for this import

- Both existing test suites passed locally with Python 3.12 using `python3 -m unittest -v test_handlers.py test_flow.py`.
- The HTTP suite used a temporary database, synthetic credentials and a separate local server. No tests were run against the production database and no content was submitted to production for this import.
- Only explicitly selected source/test/configuration files and newly written review documents were imported into a new Git history. The deployment directory, tool installations, OAuth state and their histories were not copied.
- The import was checked for the known runtime password strings, selected deployment identifiers, credential/token patterns and unexpected data/key files. This focused check is not an exhaustive secret-scanning certification.

The repository's CI results, if available, are a separate verification result. A successful test run is not a security audit. See [SECURITY.md](../SECURITY.md) for known limitations and the boundaries of the review.
