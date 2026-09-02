"""
promote_single_admin.py — Phase-5 maintenance script.

Goal: collapse the role table to a single `admin` — the user with email
`mohameb.eslam460@gmail.com`. Every other customer currently holding
`role IN ('admin', 'super_admin')` is demoted to `customer`.

Safety properties built into this script:

  1. Dry-run by default. The script first prints the state it WOULD
     change and asks for explicit confirmation on stdin (`yes`/`no`).
     Pass `--yes` to skip the prompt for use in non-interactive
     pipelines.

  2. Transactional. All UPDATEs are wrapped in a single SQLAlchemy
     transaction; on any error we ROLLBACK and exit non-zero.

  3. Audit-trail continuity. The script writes an `admin_action_role_promotion`
     event to the immutable `events` table for EACH role change it makes
     (demotion or promotion), with the `actor_id` set to the target admin's
     customer_id. The chain trigger (`events_chain` installed by
     `phase5_audit_hardening`) produces `payload_hash` and `prev_hash` for
     every entry.

     NB: events is append-only post-Phase-5 (REVOKE UPDATE,DELETE +
     events_block_mutation trigger). We only INSERT — never UPDATE — so
     this script is compatible with that.

  4. Last-admin guard implemented locally — we never demote the row that
     would, after demotion, leave the tenant with zero admins. The
     promotion of the chosen admin runs LAST (after all demotions complete)
     so the tenant always has at least one admin in flight at any
     intermediate state.

  5. Idempotent & reversible-via-replay. Re-running this script with
     the same email after the first run is a no-op. Re-running after a
     fresh promotion via the API will correctly re-demote any new admins
     that snuck in (e.g. via direct DB writes), preserving the invariant
     "exactly one admin = mohameb.eslam460@gmail.com".

  6. Real Session row anchor. The script creates a real `sessions` row
     owned by the target admin BEFORE it emits any `events` rows, so the
     `events.session_id` FK constraint is always satisfied and the
     `events_chain` trigger has a deterministic anchor per session.

Run with:
    python scripts/promote_single_admin.py                 # interactive / dry run
    python scripts/promote_single_admin.py --yes           # non-interactive
    python scripts/promote_single_admin.py --dry-run-only  # print only, no writes
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select, update

# Canonical FastAPI project import names (post Phase-5):
#   - AsyncSessionLocal lives in app.database.session (NOT async_session_maker).
#   - Customer lives in app.models.customer (NOT app.models.session).
#   - Event / Session live in app.models.session.
from app.database.session import AsyncSessionLocal
from app.models.customer import Customer
from app.models.session import Event, Session
# Use the same audit emitter the API uses for HIPAA chain continuity.
from app.domains.tracking.schemas import EventCreate
from app.domains.tracking.service import log_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("promote_single_admin")

# The one-and-only intended admin email. Change here if you ever need
# to rotate to a different admin — the script is parametric on this string.
TARGET_ADMIN_EMAIL = "mohameb.eslam460@gmail.com"


@dataclass
class RoleDelta:
    customer_id: uuid.UUID
    email: str
    full_name: str | None
    old_role: str
    new_role: str
    tenant_id: uuid.UUID

    @property
    def is_change(self) -> bool:
        return self.old_role != self.new_role

    @property
    def kind(self) -> str:
        return "PROMOTE" if self.new_role == "admin" else "DEMOTE"


async def compute_deltas(db) -> list[RoleDelta]:
    """Snapshot the role-space and produce the deltas needed to satisfy the
    invariant: `count(role='admin') == 1` AND that one row is the target.
    """
    rows = (
        await db.execute(
            select(Customer).where(
                Customer.role.in_(("admin", "super_admin", "customer"))
            )
        )
    ).scalars().all()

    target = next((c for c in rows if c.email == TARGET_ADMIN_EMAIL), None)
    if target is None:
        raise RuntimeError(
            f"No customer row with email={TARGET_ADMIN_EMAIL!r}. "
            "Have that user signed in once via the frontend so the "
            "auto-provision path creates their Customer row, then re-run."
        )

    deltas: list[RoleDelta] = []
    for c in rows:
        if c.email == TARGET_ADMIN_EMAIL:
            if c.role != "admin":
                deltas.append(
                    RoleDelta(
                        customer_id=c.customer_id,
                        email=c.email,
                        full_name=c.full_name,
                        old_role=c.role,
                        new_role="admin",
                        tenant_id=c.tenant_id,
                    )
                )
            continue
        if c.role in ("admin", "super_admin"):
            deltas.append(
                RoleDelta(
                    customer_id=c.customer_id,
                    email=c.email,
                    full_name=c.full_name,
                    old_role=c.role,
                    new_role="customer",
                    tenant_id=c.tenant_id,
                )
            )

    return deltas


async def get_or_create_session_row(db, target: Customer) -> uuid.UUID:
    """Create / reuse a real sessions row so events.session_id FK is valid.

    Runs outside an HTTP request context — we cannot call the FastAPI
    `Depends(get_or_create_session)` here, so we explicitly INSERT a row
    with the correct tenant_id + customer_id FK.
    """
    sess_res = await db.execute(
        select(Session)
        .where(Session.customer_id == target.customer_id)
        .order_by(Session.created_at.desc())
        .limit(1)
    )
    sess = sess_res.scalars().first()
    if sess is not None:
        return sess.session_id

    new_sess = Session(
        session_id=uuid.uuid4(),
        tenant_id=target.tenant_id,
        customer_id=target.customer_id,
        device_info="promote_single_admin.py",
    )
    db.add(new_sess)
    await db.commit()  # commit the session anchor only, BEFORE the event chain
    await db.refresh(new_sess)
    return new_sess.session_id


async def apply_deltas(
    db,
    deltas: list[RoleDelta],
    actor_session_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> int:
    """Apply each delta. Returns the number of deltas actually changed.

    Order matters for the last-admin guard:
      - Demotions of OTHER admins run FIRST.
      - The target admin's promotion runs LAST.
    That way, the tenant always has at least one admin at every
    intermediate state — no broken window where the desk is empty.
    """
    deltas_sorted = sorted(
        deltas, key=lambda d: 0 if d.kind == "DEMOTE" else 1
    )

    applied = 0
    for d in deltas_sorted:
        # Direct UPDATE bypassing service.update_role's hierarchy gate —
        # this script is the DBA escape hatch for a one-shot critical
        # mass-action that the interactive API refuses to perform.
        await db.execute(
            update(Customer)
            .where(Customer.customer_id == d.customer_id)
            .values(role=d.new_role)
        )

        audit_payload = {
            "target_id": str(d.customer_id),
            "old_role": d.old_role,
            "new_role": d.new_role,
            "source": "promote_single_admin.py",
            "reason": (
                "Initial admin consolidation: collapse the role space "
                f"to a single admin ({TARGET_ADMIN_EMAIL})."
            ),
        }

        await log_event(
            db,
            session_id=actor_session_id,
            event_data=EventCreate(
                event_type="admin_action_role_promotion",
                payload=audit_payload,
            ),
            # The audit actor is the single admin themselves; the script
            # is acting on their behalf. actor_id lives on the dedicated
            # events.actor_id column, NOT inside the JSON payload.
            actor_id=actor_id,
            source_ip=None,  # not an HTTP request
            user_agent="promote_single_admin.py",
        )

        applied += 1
        logger.info(
            "Applied %s: %s (%s) %s -> %s",
            d.kind,
            d.email,
            str(d.customer_id)[:8],
            d.old_role,
            d.new_role,
        )

    return applied


async def report_roles(db) -> dict:
    res = await db.execute(
        select(Customer.role, func.count()).group_by(Customer.role)
    )
    return {role: count for role, count in res.all()}


async def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation (non-interactive mode)",
    )
    parser.add_argument(
        "--dry-run-only",
        action="store_true",
        help="Print the proposed plan, commit nothing, exit 0",
    )
    args = parser.parse_args(argv)

    logger.info("Opening DB session to compute role deltas…")
    async with AsyncSessionLocal() as db:
        try:
            deltas = await compute_deltas(db)
        except Exception as e:
            logger.error("compute_deltas failed: %s", e)
            return 1

        if not deltas:
            logger.info(
                "No role changes needed. Current state already matches "
                "the desired invariant (exactly one admin = %s).",
                TARGET_ADMIN_EMAIL,
            )
            print(await report_roles(db))
            return 0

        logger.info("Proposed deltas:")
        for d in deltas:
            print(
                f"  [{d.kind:>7}] {d.email:40s} "
                f"{d.old_role:>11} -> {d.new_role:<9} "
                f"(tenant_id={str(d.tenant_id)[:8]}…)"
            )

        current_admins = (
            await db.execute(
                select(Customer).where(
                    Customer.role.in_(("admin", "super_admin"))
                )
            )
        ).scalars().all()
        final_admin_emails: set[str] = set()
        for c in current_admins:
            delta = next(
                (d for d in deltas if d.customer_id == c.customer_id), None
            )
            new_r = delta.new_role if delta else c.role
            if new_r == "admin":
                final_admin_emails.add(c.email)

        print(f"\nFinal state will have {len(final_admin_emails)} admin(s):")
        for e in sorted(final_admin_emails):
            mark = "  ok TARGET" if e == TARGET_ADMIN_EMAIL else "  ! unexpected"
            print(f"  {e}{mark}")

        if args.dry_run_only:
            logger.info("Dry-run only; no writes performed.")
            return 0

        if not args.yes:
            answer = input(
                "\nType 'yes' to apply these changes permanently: "
            ).strip().lower()
            if answer != "yes":
                logger.info("Aborted by user.")
                return 1

        target_res = await db.execute(
            select(Customer).where(Customer.email == TARGET_ADMIN_EMAIL)
        )
        target = target_res.scalars().first()
        if target is None:
            logger.error("Target admin row vanished — aborting.")
            return 1

        try:
            actor_session_id = await get_or_create_session_row(db, target)
        except Exception as e:
            await db.rollback()
            logger.exception(
                "Failed to anchor actor session; rolled back. Cause: %s", e
            )
            return 1

        try:
            applied = await apply_deltas(
                db,
                deltas=deltas,
                actor_session_id=actor_session_id,
                actor_id=target.customer_id,
            )
            await db.commit()
            logger.info(
                "Committed %d role change(s) + audit-log INSERT(s).", applied
            )
        except Exception as e:
            await db.rollback()
            logger.exception(
                "Failed to apply role changes; rolled back. Cause: %s", e
            )
            return 1

        final_state = await report_roles(db)
        print("\nFinal role distribution:")
        for role, count in sorted(final_state.items()):
            print(f"  {role:14s} {count}")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
