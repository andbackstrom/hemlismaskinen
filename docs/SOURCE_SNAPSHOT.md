# Source snapshots and verification

Initial import prepared for external review on 2026-10-19 (Europe/Stockholm).

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

## Terminal loading and optional music revision

The revision following the initial import changes the administrator login copy, adds a brief reduced-motion-aware terminal animation, and adds opt-in YouTube playback sourced from Musikhjärnan's private imported Likes capture. The source capture itself is not part of Git. The implementation and checks are reviewable in the corresponding feature pull request.

| File | SHA-256 for this revision |
| --- | --- |
| `server.py` | `d4ea85c5ecd040a9807186c8944f4b707e29719ce3747420b26b721258eda6a4` |
| `index.html` | `400957ff16ff3100515f8741c45f9e4e73713137887a6114f76cbfd0ed378b4c` |
| `compose.yaml` | `b49284c4480393724396e6eb8ed994c1bffb8030b973a0424f037f8d91fcd75f` |

Local verification: all five Python tests passed. JavaScript syntax was checked with Node. An isolated DOM simulation checked admin copy, initial/login animation and skip, reduced motion, no external player request before opt-in, safe track metadata rendering, and iframe removal on stop/logout. This is not a full-browser rendering or real YouTube playback test; playback availability and third-party restrictions depend on YouTube and the browser.

Deployment is separate from source publication. The initial checksums above are historical, not the current checksums after applying this feature.

### Runtime identity follow-up

The optional music source is private and owned by the NAS account. The container therefore runs as a configured non-root UID/GID with ownership of only this app's data and read access to the existing music capture. App source is public/readable; the original favorite file's ownership and mode are not widened. The updated `compose.yaml` SHA-256 is `eae0c386793e9edc64c9d03f1f3fb1f6d413456e69659c9c624b7099b6d4582c`. Python and HTML hashes above are unchanged.
