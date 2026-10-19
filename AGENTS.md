# HEMLISMASKINEN

This repository exists for open security review. Read README.md and SECURITY.md before changing authentication, moderation, storage, or privacy claims. Match claims to implementation and report verification limits.

Never commit runtime credentials, cookies, database files, real submissions, logs, or backups. Use synthetic fixtures and temporary data. Do not test against the deployed service or its production database.

Propose code changes in a branch and pull request. No automatic deployment exists; publishing or merging source does not authorize changes to the live server or Cloudflare configuration. Run `python3 -m unittest -v test_handlers.py test_flow.py test_music.py test_archive.py` for relevant changes.

The app uses Python's standard library and a standalone HTML/JS client. Preserve the current small architecture unless the change has a concrete security or functional reason. Do not describe no IP storage as guaranteed anonymity. Rejected posts are removed from the active table, not necessarily from snapshots or storage media.

Pausmusik must remain opt-in: never preload YouTube or a remote player before a visitor clicks. Keep the private Musikhjärnan source capture out of Git; use synthetic music fixtures. The server may return only a validated video ID and display metadata, never account tokens or the full source.
