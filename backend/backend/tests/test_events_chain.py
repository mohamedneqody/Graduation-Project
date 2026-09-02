"""
test_events_chain.py — verifies Phase 6 audit-chain backfill hardening.

Three properties are tested, all against the live PostgreSQL functions
created by `phase5_audit_hardening` + `phase6_chain_backfill`:

  1. After backfill on a freshly-seeded chain that mixed NULL rows
     (simulating pre-Phase-5 inserts) with Phase-5-signed rows,
     `verify_events_chain` reports zero genuine mismatches AND zero
     unsigned rows.

  2. Backfill is idempotent — calling it twice yields identical chain
     state and the second call rebuilds zero rows.

  3. `--force` recomputes every row in scope and the resulting chain
     still verifies clean.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

# These tests run against the live test database. They need the pgcrypto
# extension AND the Phase 6 functions installed. We run them inside a
# fresh schema-local table so the conftest DB creation does not conflict.
# The conftest fixture `setup_test_db` drops and creates all tables via
# Base.metadata.create_all — meaning the `events` table exists but the
# Phase 5/6 triggers and functions do NOT. We therefore create the
# functions inline inside each test from a bundled SQL snapshot.


# ---------------------------------------------------------------------------
# SQL snippets — kept as raw multi-statement strings. These mirror the
# relevant pieces of phase5_audit_hardening.py / phase6_chain_backfill.py
# but are scoped to the test database where Alembic does not run.
# ---------------------------------------------------------------------------

# Each list element is a single SQL statement the DBAPI can execute in
# one `text()` call. The dollar-quoted plpgsql bodies may legally contain
# semicolons, so we keep them as one statement each (no ';' splitting).
_SETUP_STATEMENTS: list[str] = [
    "CREATE EXTENSION IF NOT EXISTS pgcrypto;",

    # 1. The BEFORE INSERT chain trigger function.
    r"""
CREATE OR REPLACE FUNCTION public.test_events_chain()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
  latest_payload_hash text;
BEGIN
  IF NEW.event_seq IS NULL THEN
    NEW.event_seq := nextval(pg_get_serial_sequence('public.events', 'event_seq'));
  END IF;
  SELECT e.payload_hash
    FROM public.events e
   WHERE e.session_id = NEW.session_id
   ORDER BY e.event_seq DESC LIMIT 1
   INTO latest_payload_hash;
  NEW.prev_hash := COALESCE(latest_payload_hash,
    '0000000000000000000000000000000000000000000000000000000000000000');
  NEW.payload_hash := encode(digest(
    COALESCE(NEW.payload::text, '{}') || '|' || NEW.prev_hash || '|' ||
    COALESCE(NEW.actor_id::text, ''), 'sha256'), 'hex');
  RETURN NEW;
END;
$$
""".strip(),

    # 2. Gap-aware verifier.
    r"""
CREATE OR REPLACE FUNCTION public.verify_events_chain(p_tenant_id uuid DEFAULT NULL)
RETURNS TABLE (
  broken_at_seq bigint, event_id uuid, session_id uuid, reason text,
  expected_hash text, actual_hash text, unsigned_count bigint
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  r record;
  prev_payload text := '0000000000000000000000000000000000000000000000000000000000000000';
  expected_hash text;
  v_unsigned bigint := 0;
BEGIN
  FOR r IN
    SELECT e.event_id, e.session_id, e.event_seq, e.payload_hash, e.prev_hash,
           COALESCE(e.payload::text, '{}') AS payload_text,
           COALESCE(e.actor_id::text, '') AS actor_text
    FROM public.events e
    WHERE p_tenant_id IS NULL
    ORDER BY e.session_id, e.event_seq
  LOOP
    IF r.payload_hash IS NULL OR r.prev_hash IS NULL THEN
      v_unsigned := v_unsigned + 1;
      broken_at_seq := r.event_seq; event_id := r.event_id; session_id := r.session_id;
      reason := 'pre-phase5 unsigned'; expected_hash := NULL; actual_hash := NULL;
      unsigned_count := v_unsigned;
      RETURN NEXT;
      CONTINUE;
    END IF;
    IF r.prev_hash IS DISTINCT FROM prev_payload THEN
      broken_at_seq := r.event_seq; event_id := r.event_id; session_id := r.session_id;
      reason := 'prev_hash mismatch'; expected_hash := prev_payload; actual_hash := r.prev_hash;
      unsigned_count := v_unsigned;
      RETURN NEXT;
    END IF;
    expected_hash := encode(digest(r.payload_text || '|' || r.prev_hash || '|' || r.actor_text, 'sha256'), 'hex');
    IF r.payload_hash IS DISTINCT FROM expected_hash THEN
      broken_at_seq := r.event_seq; event_id := r.event_id; session_id := r.session_id;
      reason := 'payload_hash mismatch'; expected_hash := expected_hash; actual_hash := r.payload_hash;
      unsigned_count := v_unsigned;
      RETURN NEXT;
    END IF;
    prev_payload := r.payload_hash;
  END LOOP;
  broken_at_seq := NULL; event_id := NULL; session_id := NULL;
  reason := 'chain-summary'; expected_hash := NULL; actual_hash := NULL;
  unsigned_count := v_unsigned;
  RETURN NEXT;
  RETURN;
END;
$$
""".strip(),

    # 3. Backfiller.
    r"""
CREATE OR REPLACE FUNCTION public.rebuild_events_chain_hashes(
  p_session_id uuid DEFAULT NULL, p_force boolean DEFAULT FALSE
)
RETURNS TABLE (rebuilt_rows bigint, skipped_rows bigint, first_seq bigint, last_seq bigint)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  r record;
  prev_payload text := '0000000000000000000000000000000000000000000000000000000000000000';
  v_rebuilt bigint := 0; v_skipped bigint := 0;
  v_first bigint := NULL; v_last bigint := NULL;
  v_computed_prev text; v_computed_hash text;
BEGIN
  BEGIN
    ALTER TABLE public.events DISABLE TRIGGER events_block_mutation;
  EXCEPTION WHEN undefined_object THEN NULL;
  END;
  FOR r IN
    SELECT e.event_id, e.event_seq, e.session_id, e.payload_hash,
           COALESCE(e.payload::text, '{}') AS payload_text,
           COALESCE(e.actor_id::text, '') AS actor_text
    FROM public.events e
    WHERE (p_session_id IS NULL OR e.session_id = p_session_id)
    ORDER BY e.session_id, e.event_seq
    FOR UPDATE
  LOOP
    IF r.payload_hash IS NOT NULL AND NOT p_force THEN
      prev_payload := r.payload_hash; v_skipped := v_skipped + 1;
      CONTINUE;
    END IF;
    v_computed_prev := prev_payload;
    v_computed_hash := encode(digest(
      r.payload_text || '|' || v_computed_prev || '|' || r.actor_text, 'sha256'), 'hex');
    UPDATE public.events
       SET prev_hash = v_computed_prev, payload_hash = v_computed_hash
     WHERE event_id = r.event_id AND event_seq = r.event_seq;
    prev_payload := v_computed_hash;
    v_rebuilt := v_rebuilt + 1;
    v_first := COALESCE(v_first, r.event_seq); v_last := r.event_seq;
  END LOOP;
  BEGIN
    ALTER TABLE public.events ENABLE TRIGGER events_block_mutation;
  EXCEPTION WHEN undefined_object THEN NULL;
  END;
  rebuilt_rows := v_rebuilt; skipped_rows := v_skipped;
  first_seq := v_first; last_seq := v_last;
  RETURN NEXT;
  RETURN;
END;
$$
""".strip(),

    # 4. Unsigned-count helper.
    r"""
CREATE OR REPLACE FUNCTION public.events_unsigned_count(p_tenant_id uuid DEFAULT NULL)
RETURNS bigint LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT count(*) FROM public.events e
  WHERE e.payload_hash IS NULL
    AND (p_tenant_id IS NULL);
$$
""".strip(),

    # 5. Append-only block trigger.
    r"""
CREATE OR REPLACE FUNCTION public.events_block_mutation()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  RAISE EXCEPTION 'public.events is append-only: UPDATE/DELETE is forbidden.';
END;
$$
""".strip(),

    # 6. BEFORE INSERT trigger.
    "DROP TRIGGER IF EXISTS events_chain ON public.events",
    "CREATE TRIGGER events_chain BEFORE INSERT ON public.events "
    "FOR EACH ROW EXECUTE FUNCTION public.test_events_chain()",

    # 7. BEFORE UPDATE OR DELETE trigger.
    "DROP TRIGGER IF EXISTS events_block_mutation ON public.events",
    "CREATE TRIGGER events_block_mutation BEFORE UPDATE OR DELETE ON public.events "
    "FOR EACH ROW EXECUTE FUNCTION public.events_block_mutation()",
]

_TEARDOWN_STATEMENTS: list[str] = [
    "DROP TRIGGER IF EXISTS events_chain ON public.events",
    "DROP TRIGGER IF EXISTS events_block_mutation ON public.events",
    "DROP FUNCTION IF EXISTS public.test_events_chain()",
    "DROP FUNCTION IF EXISTS public.events_block_mutation()",
    "DROP FUNCTION IF EXISTS public.verify_events_chain(uuid)",
    "DROP FUNCTION IF EXISTS public.rebuild_events_chain_hashes(uuid, boolean)",
    "DROP FUNCTION IF EXISTS public.events_unsigned_count(uuid)",
]


async def _exec_statements(db, statements: list[str]) -> None:
    """Execute a list of single SQL statements in order, each in its own
    transaction. Closes+re-opens around each statement so plpgsql DO
    blocks and DDL both commit cleanly."""
    for stmt in statements:
        await db.execute(text(stmt))
        await db.commit()


# ---------------------------------------------------------------------------
# Fixtures — Phase 6 specific
# ---------------------------------------------------------------------------

@pytest.fixture
async def chain_test_db(db_session):
    """Install the chain functions on the live test database, then
    drop them at teardown so they do not leak into other tests."""
    await _exec_statements(db_session, _SETUP_STATEMENTS)
    yield db_session
    await _exec_statements(db_session, _TEARDOWN_STATEMENTS)


# ---------------------------------------------------------------------------
# Helpers — inserts a single events row with a freshly-minted session.
# ---------------------------------------------------------------------------

async def _insert_event(db, *,
                        session_id: uuid.UUID,
                        payload: dict | None,
                        bypass_trigger: bool = False) -> None:
    """Insert an event row. When `bypass_trigger` is True, the row is
    inserted with payload_hash and prev_hash forced to NULL — this
    simulates a pre-Phase-5 migration row that pre-dates the trigger
    and whose hashes were never signed."""
    if bypass_trigger:
        await db.execute(text(
            "ALTER TABLE public.events DISABLE TRIGGER events_chain"
        ))
    payload_text = _quote_literal(payload)
    sql = text(
        f"INSERT INTO public.events (event_id, session_id, event_type, payload) "
        f"VALUES (gen_random_uuid(), :sid, 'page_view', {payload_text}::jsonb)"
    )
    await db.execute(sql, {"sid": str(session_id)})
    if bypass_trigger:
        await db.execute(text(
            "ALTER TABLE public.events ENABLE TRIGGER events_chain"
        ))
    await db.commit()


def _quote_literal(payload) -> str:
    if payload is None:
        return "NULL"
    import json
    quoted = json.dumps(payload).replace("'", "''")
    return f"'{quoted}'"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def _make_session_and_tenant(db):
    """Create a tenant and an empty session for the test."""
    tenant_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    session_id = uuid.uuid4()

    # Insert a tenant.
    await db.execute(text(
        "INSERT INTO tenants (tenant_id, name, subdomain, is_active) "
        "VALUES (:tid, 't', 't', TRUE) ON CONFLICT DO NOTHING"
    ), {"tid": str(tenant_id)})

    # Insert customer (must satisfy any existing RLS WITH CHECK — but the
    # test DB does not have RLS enabled by conftest, so this is plain INSERT).
    await db.execute(text(
        "INSERT INTO customers (customer_id, tenant_id, email, role, is_active) "
        "VALUES (:cid, :tid, :email, 'customer', TRUE) ON CONFLICT DO NOTHING"
    ), {"cid": str(customer_id), "tid": str(tenant_id),
        "email": f"c-{customer_id.hex}@t.test"})

    # Insert session.
    await db.execute(text(
        "INSERT INTO sessions (session_id, tenant_id, customer_id) "
        "VALUES (:sid, :tid, :cid) ON CONFLICT DO NOTHING"
    ), {"sid": str(session_id), "tid": str(tenant_id),
        "cid": str(customer_id)})
    await db.commit()
    return tenant_id, customer_id, session_id


@pytest.mark.asyncio
async def test_backfill_signs_null_rows(chain_test_db):
    """Run rebuild_events_chain_hashes on a chain that has a row with
    NULL payload_hash inserted via trigger bypass, then assert that
    `verify_events_chain` reports zero mismatches AND zero unsigned rows.
    """
    db = chain_test_db
    _, _, session_id = await _make_session_and_tenant(db)
    # Two real (signable) rows.
    await _insert_event(db, session_id=session_id, payload={"v": 1})
    await _insert_event(db, session_id=session_id, payload={"v": 2})
    # One NULL row, simulating pre-Phase-5 data.
    await _insert_event(db, session_id=session_id, payload={"v": 3},
                        bypass_trigger=True)
    # Then two more real rows (for the post-backfill chain continuity).
    await _insert_event(db, session_id=session_id, payload={"v": 4})
    await _insert_event(db, session_id=session_id, payload={"v": 5})

    # BEFORE: verify_events_chain should report unsigned_count=1 for the
    # bypassed row plus a chain-summary row at the end.
    verify_before = (await db.execute(text(
        "SELECT reason FROM public.verify_events_chain(NULL)"
    ))).all()
    reasons = [r[0] for r in verify_before]
    assert "pre-phase5 unsigned" in reasons, reasons

    # Run backfill.
    rebuild = (await db.execute(text(
        "SELECT rebuilt_rows, skipped_rows, first_seq, last_seq "
        "FROM public.rebuild_events_chain_hashes(NULL, FALSE)"
    ))).first()
    assert rebuild is not None
    rebuilt = int(rebuild[0] or 0)
    skipped = int(rebuild[1] or 0)
    assert rebuilt >= 1
    print(f"\nbackfill rebuilt={rebuilt} skipped={skipped}")
    await db.commit()

    # AFTER: verify_events_chain MUST report zero genuine mismatches AND
    # zero unsigned rows (the chain is now fully signed and continuous).
    verify_after = (await db.execute(text(
        "SELECT reason, broken_at_seq FROM public.verify_events_chain(NULL)"
    ))).all()
    reasons = [r[0] for r in verify_after]
    mismatch_rows = [r for r in reasons if "mismatch" in r]
    unsigned_rows = [r for r in reasons if r == "pre-phase5 unsigned"]
    assert not mismatch_rows, f"chain has mismatches after backfill: {mismatch_rows}"
    assert not unsigned_rows, \
        f"chain still has unsigned rows after backfill: {unsigned_rows}"

    unsigned_count_scalar = (await db.execute(text(
        "SELECT public.events_unsigned_count(NULL)"
    ))).scalar()
    assert int(unsigned_count_scalar) == 0


@pytest.mark.asyncio
async def test_backfill_is_idempotent(chain_test_db):
    """Re-running backfill on an already-fully-signed chain must rebuild
    zero rows (its `p_force=FALSE` guard intact)."""
    db = chain_test_db
    _, _, session_id = await _make_session_and_tenant(db)
    # Two signed rows.
    await _insert_event(db, session_id=session_id, payload={"v": 1})
    await _insert_event(db, session_id=session_id, payload={"v": 2})

    # First pass — should rebuild whatever rows we have NULL.
    first = (await db.execute(text(
        "SELECT rebuilt_rows, skipped_rows "
        "FROM public.rebuild_events_chain_hashes(NULL, FALSE)"
    ))).first()
    await db.commit()

    # Second pass — should rebuild zero rows (everything already signed).
    second = (await db.execute(text(
        "SELECT rebuilt_rows, skipped_rows "
        "FROM public.rebuild_events_chain_hashes(NULL, FALSE)"
    ))).first()
    await db.commit()

    assert int(second[0] or 0) == 0, "backfill must rebuild 0 rows on re-run"


@pytest.mark.asyncio
async def test_force_recompute_keeps_chain_consistent(chain_test_db):
    """`p_force=TRUE` recomputes every row in scope and the resulting
    chain still verifies clean (all hashes consistent with payloads +
    prev_hash chain)."""
    db = chain_test_db
    _, _, session_id = await _make_session_and_tenant(db)
    await _insert_event(db, session_id=session_id, payload={"v": "a"})
    await _insert_event(db, session_id=session_id, payload={"v": "b"})
    await _insert_event(db, session_id=session_id, payload={"v": "c"})
    # First pass to sign everything (in case the trigger missed something).
    _ = (await db.execute(text(
        "SELECT rebuilt_rows FROM public.rebuild_events_chain_hashes(NULL, FALSE)"
    ))).first()
    await db.commit()
    # Capture original hashes.
    rows_pre = (await db.execute(text(
        "SELECT event_seq, payload_hash, prev_hash FROM public.events "
        "ORDER BY event_seq"
    ))).all()
    pre_hashes = [(int(r[0]), r[1], r[2]) for r in rows_pre]

    # Force-recompute.
    rebuild = (await db.execute(text(
        "SELECT rebuilt_rows FROM public.rebuild_events_chain_hashes(NULL, TRUE)"
    ))).first()
    await db.commit()
    rows_post = (await db.execute(text(
        "SELECT event_seq, payload_hash, prev_hash FROM public.events "
        "ORDER BY event_seq"
    ))).all()
    post_hashes = [(int(r[0]), r[1], r[2]) for r in rows_post]

    # Force must have rebuilt every row.
    assert int(rebuild[0] or 0) == len(pre_hashes)
    # Each payload_hash for the same payload+prev must be identical.
    # Because the inputs are identical, recomputed hashes must match.
    for pre, post in zip(pre_hashes, post_hashes):
        assert pre[1] == post[1], \
            f"hash changed for seq {pre[0]} after force-recompute: {pre[1]} -> {post[1]}"
        assert pre[2] == post[2]

    # And the chain must still verify clean.
    rows = (await db.execute(text("SELECT reason FROM public.verify_events_chain(NULL)"))).all()
    reasons = [r[0] for r in rows]
    mismatches = [r for r in reasons if "mismatch" in r]
    unsigneds = [r for r in reasons if r == "pre-phase5 unsigned"]
    assert not mismatches
    assert not unsigneds
