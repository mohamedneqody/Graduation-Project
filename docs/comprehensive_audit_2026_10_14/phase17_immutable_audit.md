# Phase 17 — immutable audit and WORM transport

Date: 2026-10-26

## Result

- Implemented durable, tenant-scoped Supabase reservations for WORM alerts and head anchors. Deterministic IDs suppress duplicate sends across worker restarts; only proven unsent requests can retry, at most three attempts. Unknown outcomes require reconciliation.
- Implemented an optional AWS S3 Object Lock sink, disabled by default. It validates the local hash chain, uses conditional content-addressed uploads, and verifies exact bytes plus COMPLIANCE retention on a specific object version before producing a receipt. No bucket/account/policy creation or retention extension is implemented.
- Added read-only deployment readiness/verification probe and operator documentation. The local receipt is explicitly a retrieval hint, not independent immutable proof.

## Verification

- Isolated regression suite: 52 passed, 7 existing framework deprecation warnings. No live sockets, real database, production worker, cloud upload, or business message.
- XML: phase17_worm_suite.xml
- Read-only deployment probe: phase17_immutable_readiness.json; exit 2 expected because disabled/unconfigured.
- Probe reports immutable_verified=false, enabled=false, all four configuration-presence fields false, public_data_changed=false.
- Scoped git diff --check: passed (line-ending notices only).

## Remaining external dependency

The user has no AWS/S3 account. No account or bucket was created and no SDK installed. Actual external immutable storage remains unconfigured and has NOT been verified. GitHub history or Telegram/n8n acceptance must not be described as equivalent to COMPLIANCE Object Lock. Provisioning an appropriate external provider and explicitly choosing retention are later operator decisions.

## Files

- backend/app/core/immutable_audit.py
- backend/app/core/worm_dispatch.py
- backend/app/core/worm_worker.py
- backend/app/core/config.py (optional WORM fields only)
- backend/.env.example (disabled defaults)
- backend/requirements-immutable-audit.txt
- backend/scripts/probe_immutable_audit.py
- backend/tests/test_immutable_audit.py
- backend/tests/test_worm_dispatch_safety.py
- backend/tests/test_worm_worker_wiring.py
- backend/docs/immutable-audit.md
- .gitignore (exclude receipt directories)

## Operational limitations documented

- A verified snapshot establishes protection of that version until its retention deadline, not correctness/completeness of source events or future exports.
- Identical corruption fingerprints are deduplicated, including recurrence; operator review is required.
- If the ledger changes before an unsent anchor is retried, that old unsent row can remain pending while the current head is anchored. No unknown outcome is automatically resent.
- Existing snapshot retention is never extended silently; expired/mismatched evidence requires review.
- The read-only --verify-ledger command verifies the current local snapshot. It does not reconstruct an older snapshot from a receipt.
