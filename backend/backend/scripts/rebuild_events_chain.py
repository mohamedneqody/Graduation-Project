"""
rebuild_events_chain.py — Phase 6 maintenance script.

Backfills `events.payload_hash` and `events.prev_hash` for every event row
left NULL by the pre-Phase-5 chain trigger, then verifies that the audit
chain is fully signed and continuous.

Use cases:

  * Run immediately after deploying `phase6_chain_backfill` to retro-fit
    integrity hashes onto historical audit rows so `verify_events_chain()`
    stops reporting false-positive `prev_hash mismatch` breaks.
  * Run again any time a direct-SQL INSERT (e.g. another maintenance
    script) bypasses the `events_chain` BEFORE INSERT trigger and leaves
    NULL hashes behind — the `--force` flag will recompute ALL rows for
    the given session.

Safety properties built into this script:

  1. Dry-run by default. Prints the BEFORE / AFTER of
     `verify_events_chain()` and `events_unsigned_count()` and asks
     for explicit confirmation (`yes`/`no`) before applying.
     Pass `--yes` for non-interactive CI pipelines.

  2. RLS bypass is local to the SQL function only. The Python side
     connects as the normal application role; the SECURITY DEFINER
     function `rebuild_events_chain_hashes` is the only component that
     escalates, and only for the duration of the backfill transaction.

  3. Idempotent. Re-running with no flags is a no-op once all rows are
     signed (the function skips rows whose `payload_hash IS NOT NULL`
     unless `--force` is set).

  4. Append-only preservation. The `events_block_mutation` BEFORE
     UPDATE OR DELETE trigger is DISABLED inside the function then
     RE-ENABLED on exit — even on exception. We never DELETE rows.

  5. Auditable. Reports before/after counts and emits a final report
     in machine-readable JSON when `--json` is set, so CI can assert.

Run with:

    python scripts/rebuild_events_chain.py                # interactive dry run
    python scripts/rebuild_events_chain.py --yes          # apply
    python scripts/rebuild_events_chain.py --dry-run-only  # never apply
    python scripts/rebuild_events_chain.py --session-id <UUID>  # scope to one session
    python scripts/rebuild_events_chain.py --force        # recompute ALL rows in scope
    python scripts/rebuild_events_chain.py --json         # machine-readable output
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, asdict
from typing import Optional
from uuid import UUID

from sqlalchemy import text

from app.database.session import AsyncSessionLocal


log = logging.getLogger("rebuild_events_chain")


# ---------------------------------------------------------------------------
# CLI model
# ---------------------------------------------------------------------------

@dataclass
class ChainReport:
    """Snapshot of chain integrity at a point in time."""
    mismatch_count: int
    unsigned_count: int
    first_break_seq: Optional[int]
    first_break_reason: Optional[str]
    first_break_event_id: Optional[str]
    first_break_session_id: Optional[str]
    first_break_expected: Optional[str]
    first_break_actual: Optional[str]
    summary_unsigned: int

    @classmethod
    def empty(cls) -> "ChainReport":
        return cls(
            mismatch_count=0,
            unsigned_count=0,
            first_break_seq=None,
            first_break_reason=None,
            first_break_event_id=None,
            first_break_session_id=None,
            first_break_expected=None,
            first_break_actual=None,
            summary_unsigned=0,
        )


@dataclass
class BackfillResult:
    rebuilt_rows: int
    skipped_rows: int
    first_seq: Optional[int]
    last_seq: Optional[int]


# ---------------------------------------------------------------------------
# Backend calls
# ---------------------------------------------------------------------------

_VERIFY_SQL = text("""
    SELECT broken_at_seq, event_id, session_id, reason, expected_hash, actual_hash, unsigned_count
      FROM public.verify_events_chain(NULL)
     ORDER BY broken_at_seq NULLS LAST
""")

_UNSIGNED_COUNT_SQL = text("SELECT public.events_unsigned_count(NULL);")

_REBUILD_SQL = text("""
    SELECT rebuilt_rows, skipped_rows, first_seq, last_seq
      FROM public.rebuild_events_chain_hashes(:session_id, :force)
""")

_TENANT_REBUILD_SQL = text("""
    SELECT rebuilt_rows, skipped_rows, first_seq, last_seq
      FROM public.rebuild_events_chain_hashes(:session_id, :force)
""")


async def collect_report(db) -> ChainReport:
    """Run verify_events_chain and summarise the result set."""
    rows = (await db.execute(_VERIFY_SQL)).all()
    mismatch_count = 0
    unsigned_count = 0
    summary_unsigned = 0
    first = None
    for row in rows:
        reason = getattr(row, "reason", None)
        if reason == "chain-summary":
            summary_unsigned = int(getattr(row, "unsigned_count", 0) or 0)
            continue
        if reason == "pre-phase5 unsigned":
            unsigned_count += 1
        elif reason and "mismatch" in reason:
            mismatch_count += 1
            if first is None:
                first = row
        else:
            # Defensive: anything else counts as a genuine break.
            mismatch_count += 1
            if first is None:
                first = row

    if first is None:
        return ChainReport(
            mismatch_count=mismatch_count,
            unsigned_count=unsigned_count,
            first_break_seq=None,
            first_break_reason=None,
            first_break_event_id=None,
            first_break_session_id=None,
            first_break_expected=None,
            first_break_actual=None,
            summary_unsigned=summary_unsigned,
        )
    return ChainReport(
        mismatch_count=mismatch_count,
        unsigned_count=unsigned_count,
        first_break_seq=getattr(first, "broken_at_seq", None),
        first_break_reason=getattr(first, "reason", None),
        first_break_event_id=str(getattr(first, "event_id", None))
        if getattr(first, "event_id", None) is not None else None,
        first_break_session_id=str(getattr(first, "session_id", None))
        if getattr(first, "session_id", None) is not None else None,
        first_break_expected=getattr(first, "expected_hash", None),
        first_break_actual=getattr(first, "actual_hash", None),
        summary_unsigned=summary_unsigned,
    )


async def call_rebuild(db, session_id: Optional[UUID], force: bool) -> BackfillResult:
    params = {
        "session_id": str(session_id) if session_id else None,
        "force": force,
    }
    row = (await db.execute(_REBUILD_SQL, params)).first()
    return BackfillResult(
        rebuilt_rows=int(getattr(row, "rebuilt_rows", 0) or 0),
        skipped_rows=int(getattr(row, "skipped_rows", 0) or 0),
        first_seq=int(getattr(row, "first_seq", 0) or 0) or None,
        last_seq=int(getattr(row, "last_seq", 0) or 0) or None,
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def format_report(label: str, report: ChainReport) -> str:
    lines = [
        f"=== {label} ===",
        f"  genuine hash mismatches : {report.mismatch_count}",
        f"  unsigned (pre-phase5)   : {report.unsigned_count}",
        f"  summary unsigned_count  : {report.summary_unsigned}",
    ]
    if report.first_break_reason:
        lines.extend([
            f"  first break at seq      : {report.first_break_seq}",
            f"  reason                  : {report.first_break_reason}",
            f"  event_id                : {report.first_break_event_id}",
            f"  session_id              : {report.first_break_session_id}",
            f"  expected_hash           : {report.first_break_expected}",
            f"  actual_hash             : {report.first_break_actual}",
        ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(args: argparse.Namespace) -> int:
    session_id: Optional[UUID] = None
    if args.session_id:
        try:
            session_id = UUID(args.session_id)
        except ValueError:
            print(f"ERROR: --session-id {args.session_id!r} is not a valid UUID", file=sys.stderr)
            return 2

    async with AsyncSessionLocal() as db:
        log.debug("collecting BEFORE report…")
        before = await collect_report(db)
        print(format_report("BEFORE", before))

        if before.mismatch_count == 0 and before.unsigned_count == 0:
            print("\n[skip] chain already fully signed and continuous — nothing to do.")
            if args.json:
                print(json.dumps({
                    "applied": False,
                    "before": asdict(before),
                    "backfill": None,
                    "after": asdict(before),
                }, indent=2))
            return 0

        if args.dry_run_only:
            print("\n[dry-run-only] no writes performed.")
            if args.json:
                print(json.dumps({
                    "applied": False,
                    "before": asdict(before),
                    "backfill": None,
                    "after": asdict(before),
                }, indent=2))
            return 0

        if not args.yes:
            print("\nAbout to backfill NULL payload_hash/prev_hash on events.")
            confirm = input("Type 'yes' to proceed: ").strip().lower()
            if confirm != "yes":
                print("[abort] user declined.")
                return 1

        log.debug("invoking rebuild_events_chain_hashes(%s, %s)…",
                  session_id, args.force)
        result = await call_rebuild(db, session_id, args.force)
        await db.commit()
        print(f"\nbackfill result: rebuilt={result.rebuilt_rows} "
              f"skipped={result.skipped_rows} "
              f"first_seq={result.first_seq} last_seq={result.last_seq}")

        log.debug("collecting AFTER report…")
        after = await collect_report(db)
        print(format_report("AFTER", after))

        if args.json:
            print(json.dumps({
                "applied": True,
                "before": asdict(before),
                "backfill": asdict(result),
                "after": asdict(after),
            }, indent=2))

        if after.mismatch_count > 0:
            print("\n[warn] chain still has genuine mismatches after backfill — "
                  "investigate the first break listed above.", file=sys.stderr)
            return 3

        if after.unsigned_count > 0:
            print("\n[warn] some rows remain unsigned after backfill — "
                  "those rows had NULL payload and NULL event_seq; "
                  "inspect them manually.", file=sys.stderr)
            return 4

        print("\n[ok] chain fully signed and continuous.")
        return 0


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Backfill NULL payload_hash/prev_hash on the events audit chain."
    )
    p.add_argument("--yes", action="store_true",
                   help="Skip the interactive confirmation prompt.")
    p.add_argument("--dry-run-only", action="store_true",
                   help="Print the BEFORE report only; never apply any writes.")
    p.add_argument("--session-id", default=None,
                   help="Scope the backfill to a single session UUID.")
    p.add_argument("--force", action="store_true",
                   help="Recompute hashes for every row in scope — "
                        "NOT recommended outside of an explicit recovery")
    p.add_argument("--json", action="store_true",
                   help="Emit a machine-readable JSON summary on stdout.")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="Verbose logging.")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\n[abort] interrupted by user.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
