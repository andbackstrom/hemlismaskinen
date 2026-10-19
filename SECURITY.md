# Security review and disclosure

This repository publishes an initial implementation for independent review. It has not had an independent security audit and must not be described as guaranteeing anonymity or being hardened for hostile public traffic. Application changes are reviewed in branches and pull requests; record the deployed commit separately when assessing the running service.

## Reporting

Use this repository's **Security → Report a vulnerability** when private vulnerability reporting is enabled. Do not place credentials, real submitted content, or exploit details that expose users into a public issue. General design discussions and non-sensitive improvements can use issues or pull requests. No bounty, response deadline, or blanket authorization to test the live service is offered. Reproduce findings on an isolated instance with synthetic data.

## Trust boundaries

1. A browser submits a shared board password or an independent administrator password over HTTPS to a proxy/tunnel. TLS terminates outside this application.
2. The proxy forwards requests to the Python HTTP server. The server does not read or store a client IP or Cloudflare identity header in its records. This does not prevent the proxy or network operator from observing traffic.
3. The app uses a signed role-and-expiry cookie. Every authenticated reader can submit and read approved posts; only the admin role can read pending posts and approve or reject them.
4. SQLite and runtime environment variables are accessible to the host/container administrator. Content is not encrypted end to end. The operator and anyone with storage-level access can read pending and approved content.
5. Optional pause music reads a private, read-only imported YouTube Likes JSON file. `/api/music` requires reader/admin authentication and returns only a validated video ID and bounded display metadata. The browser creates a `youtube-nocookie.com` iframe only after a visitor clicks the clearly labelled button. That opt-in sends connection metadata to YouTube; closing the player removes the iframe, not data already received. The element referrer policy sends the site origin for embedded playback, not page paths or post content. No account credentials are used by this integration.
6. Submitted aliases and text are untrusted. The frontend escapes them before HTML insertion. SQL uses bound parameters.

Assets to protect include both shared passwords, the session-signing secret, pending submissions, approved content, moderation authority, and service availability. Relevant adversaries include anonymous visitors, a reader trying to become admin, a hostile webpage issuing cross-origin requests, someone with a stolen cookie, and parties observing network or storage metadata. Host administrators and the HTTPS termination infrastructure are inside the operational trust boundary.

## Known limitations and review priorities

These are observations from source inspection, not a completed exploit assessment:

- **Login and resource exhaustion:** no effective rate limit, per-account lockout, connection timeout, or request-concurrency cap. A 0.5-second pause on failed passwords is not a rate limit. ThreadingHTTPServer can create many threads; slow/incomplete bodies and repeated writes deserve attention. There is no submission quota or database size cap.
- **HTTP implementation:** Python's standard-library `http.server` is a small server, not a hardened production frontend. Review malformed headers, Content-Length handling, buffering, connection lifetime, and exception behavior behind the actual proxy.
- **Secret handling:** passwords are plaintext runtime values and compared using constant-time comparison of SHA-256 digests. This is not password hashing at rest. Startup rejects missing environment variables but does not reject empty, weak, identical, or too-short values. The deployment needs independent strong secrets, protected runtime configuration, and an explicit rotation procedure.
- **Stateless sessions:** cookies contain role, expiration, and an HMAC, and expire after eight hours. They have no per-session revocation or account store. Logout only removes the browser's cookie; a copied cookie remains usable until expiry or signing-key rotation. Password changes alone do not revoke existing cookies. Cookies are not fingerprinting protection; their exact expiry can be observable and a proxy could correlate them.
- **Browser boundary:** mutations validate the Origin header, and cookies use HttpOnly, SameSite=Strict and Secure by default. These are browser mitigations, not protection against an authorized client constructing its own requests. CSP permits inline scripts and styles; cookies do not use a `__Host-` prefix. Review XSS, sibling-subdomain cookie behavior, and how proxy HTTPS settings interact with these controls.
- **Third-party playback:** privacy-enhanced embedding is not anonymous playback. YouTube can observe connection information after opt-in and may restrict playback, use cookies or other storage, or reject embedding. Source imports may be incomplete or stale, and channel names are not guaranteed artist identities. The app does not fetch or proxy video content.
- **Privacy:** aliases, exact timestamps, language, and content can identify someone. No IP column does not establish total anonymity. The operator can read content, and proxy/CDN/ISP/DNS metadata may exist. No review of infrastructure logging, analytics, retention or backups is established by this source release.
- **Deletion:** rejecting a post performs SQL DELETE against the active database. It does not guarantee forensic erasure from SQLite pages/journals, filesystem snapshots, or backups. There is no retention schedule or interface to remove approved posts.
- **Runtime and supply chain:** the container uses an explicitly configured non-root UID/GID, but the host must grant that identity access to the app data and private read-only music source. Its Python image uses a mutable tag. The profile requests a PID cap, but some target NAS kernels discard that cap. No end-to-end browser QA, adversarial load test, or dependency/image security audit is established.

## Existing checks and their limits

The test suites cover missing/incorrect credentials, Origin rejection, reader/admin authorization, hidden pending content, approval preserving original fields, rejection deleting the active record, the stored column set, and an HTTP flow including logout. The HTTP test also checks that its isolated flow produces no process stdout/stderr. These checks do not certify proxy logging behavior, comprehensive XSS resistance, TLS setup, cookie theft resistance, resource exhaustion resilience, or secure data erasure.

## Review changes and deployment

Use a feature branch and a pull request for proposed fixes. Keep secrets and real data out of examples and fixtures. A merge or a successful CI run does not deploy this service. Report the reviewed commit and the environment used to reproduce a finding. Verify which source revision is running before making conclusions about production.
