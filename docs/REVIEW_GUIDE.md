# Reviewer guide

Start with [SECURITY.md](../SECURITY.md). Inspect the current behavior before proposing a different design; do not treat documented intentions as verified protections.

## Entry points

| Route | Authentication | Behavior |
| --- | --- | --- |
| `GET /`, `/admin`, `/anonymitet` | None | Returns the same client shell; does not itself include submitted data. |
| `GET /api/session` | Optional | Validated role or null. |
| `POST /api/login` | Password | Board password gives reader; username `andreas` selects the separate admin password. |
| `POST /api/logout` | None | Clears the browser cookie; does not revoke a copied cookie. |
| `GET /api/music` | Reader/admin | Random imported liked YouTube video with bounded title/channel metadata; never returns the full private capture. |
| `GET /api/secrets` | Reader/admin | Up to 500 approved posts, newest original date first. |
| `POST /api/secrets` | Reader/admin | Creates pending content with a random ID and server-generated UTC date. |
| `GET /api/archive` | Admin | Expired approved posts, with validated offset pagination (500 per page). |
| `GET /api/pending` | Admin | Up to 500 pending posts. |
| `POST /api/moderate` | Admin | `approve` publishes a pending row for 30 days; `reject` deletes a pending row; `republish` starts a fresh 30-day window only for expired approved rows. Original text, alias and submission time remain intact. |

POST requests require an exact Origin match and a JSON object. The declared request size is bounded at 12,000 bytes; secret text is 1–2,000 characters and alias is at most 40 characters. Examine how these checks behave for malformed or incomplete input; the limits do not bound connection time, concurrency, or total storage.

## Files

- `server.py`: `role()` and `cookie()` implement HMAC validation and expiry; `do_POST()` selects passwords and checks authorization; each database operation uses parameter binding.
- `index.html`: `esc()` is used for aliases, text, and metadata; `api()` dispatches JSON; rendering and client-side role checks are conveniences and must not replace server authorization. `/admin` is deliberately visible, not a security secret.
- `compose.yaml`: persistence and transport assumptions, writable mounts, capabilities, memory and requested PID limits, logging and port binding.
- Tests use only synthetic data and temporary storage; their known passwords do not authenticate to the deployed service.

## Useful investigations

Compare the intended privacy claims with the actual session cookie and proxy behavior. Review role forgery, cookie expiry and revocation, XSS rendering, cross-origin writes, input edge cases, moderation state transitions, SQLite remanence and error paths. Investigate brute force, thread/connection exhaustion, slow bodies, write amplification, and storage growth only in an isolated environment.

Document both the expected and observed result, the exact commit, and a minimal synthetic reproduction. Suggested fixes can be proposed independently; this repository is not a claim that those fixes have already shipped.

For pause music, verify that opening or logging into the page makes no third-party requests. Clicking the music button may create one iframe from `youtube-nocookie.com`; verify that closing it or logging out removes it. Only valid 11-character video IDs with `list=LM` evidence are selected. Missing or malformed sources must return 503, without revealing paths. The source file is private runtime data and must not be committed. The loading animation is decorative and does not establish an anonymity, encryption or erasure guarantee; reduced-motion users skip it.

Expiry review: check the exact 30-day boundary, delayed approval of an old submission, preservation of original fields, malformed/null publication dates failing closed, role/Origin denial for republishing, stale/double clicks returning 409, migration from the old five-column schema, idempotent startup and archive pagination. The glowing loading phrases are static fiction; they never expose submitted content. Normal animation duration is three seconds, with skip and reduced-motion exceptions.
