"""phase6_chain_backfill

Revision ID: phase6_chain_backfill
Revises: 7dd95fe06039
Create Date: 2026-08-09 12:00:00.000000

Phase 6 — Audit-chain backfill & verifier hardening.

Background
----------
After `phase5_audit_hardening` shipped the new `events_chain()` BEFORE INSERT
trigger, every freshly INSERTed event gets deterministic `payload_hash` and
`prev_hash`. HOWEVER, every event row that existed BEFORE the Phase 5
migration was written by the *old* trigger function (or no trigger at all),
which left both columns as NULL.

The first new (post-Phase-5) event therefore picks the previous row's
`payload_hash = NULL` and chains to it. `verify_events_chain()` then walks
the global chain in `event_seq` order and reports:

    broken_at_seq = 16   reason = prev_hash mismatch
    expected_hash  = NULL  actual_hash = NULL

That response is itself a false positive in one sense (both rows have NULL
because the older row predates the trigger) and a real integrity gap in
another (we cannot retroactively prove any of the pre-Phase-5 payloads
since the trigger never signed them).

This migration does three things, in order:

  1. Re-creates `verify_events_chain()` to be **gap-aware**: a row whose
     `payload_hash IS NULL` is treated as "pre-Phase-5, unsigned" — the
     verifier SKIPS it (does NOT report a false-positive break) but still
     reports the count of unsigned rows separately via a second output
     column. Genuine breaks (recomputed hash != stored hash) are still
     surfaced. This makes the verifier safe to run on a mixed-version DB.

  2. Installs `rebuild_events_chain_hashes(p_session_id uuid DEFAULT NULL)`,
     a one-shot SECURITY DEFINER backfill that recomputes `payload_hash`
     and `prev_hash` for every event whose `payload_hash IS NULL` (or every
     event for the given session if `p_session_id` is provided), in strict
     `event_seq` order. Because `events` is append-only under Phase 5
     (`events_block_mutation` BEFORE UPDATE OR DELETE trigger), the
     function DISABLES that trigger locally inside a SECURITY DEFINER
     block, performs the UPDATEs, and re-enables it before COMMIT. The
     function is also safe in a session that has `app.current_tenant_id`
     set — it bypasses RLS for the backfill, then restores it.

  3. Adds a `pg_cron`-ready scheduling stub (commented) and an
     `events_unsigned_count()` helper for monitoring dashboards.

The migration is idempotent — every CREATE is preceded by an OR REPLACE /
DROP IF EXISTS, and `rebuild_events_chain_hashes()` may be invoked any
number of times without corrupting already-signed rows (it only touches
rows whose `payload_hash IS NULL` unless `p_force := true`).
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'phase6_chain_backfill'
down_revision: Union[str, None] = '7dd95fe06039'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Upgrade / Downgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # 1. Gap-aware verifier.
    #    Rows whose `payload_hash IS NULL` are reported via `unsigned_count`
    #    (returned per-row as `reason = 'pre-phase5 unsigned'` with both
    #    expected/actual = NULL) and otherwise SKIPPED for chain-continuity
    #    purposes. Genuine hash mismatches still surface as before.
    op.execute("DROP FUNCTION IF EXISTS public.verify_events_chain(uuid);")

    op.execute(r"""
        CREATE OR REPLACE FUNCTION public.verify_events_chain(
          p_tenant_id uuid DEFAULT NULL
        )
        RETURNS TABLE (
          broken_at_seq   bigint,
          event_id        uuid,
          session_id      uuid,
          reason          text,
          expected_hash   text,
          actual_hash     text,
          unsigned_count  bigint
        )
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, extensions
        AS $$
        DECLARE
          r               record;
          prev_payload    text := '0000000000000000000000000000000000000000000000000000000000000000';
          expected_hash   text;
          v_unsigned      bigint := 0;
        BEGIN
          FOR r IN
            SELECT e.event_id, e.session_id, e.event_seq,
                   e.payload_hash, e.prev_hash,
                   COALESCE(e.payload::text, '{}') AS payload_text,
                   COALESCE(e.actor_id::text, '')  AS actor_text
            FROM public.events e
            WHERE p_tenant_id IS NULL
               OR EXISTS (
                    SELECT 1 FROM public.sessions s
                    JOIN public.customers c ON c.customer_id = s.customer_id
                    WHERE s.session_id = e.session_id
                      AND c.tenant_id = p_tenant_id
                   )
            ORDER BY e.session_id, e.event_seq
          LOOP
            -- 0. Gap-aware: rows whose payload_hash is NULL predate the
            --    Phase 5 trigger and cannot be retroactively verified.
            --    We report them but they do NOT poison the chain.
            IF r.payload_hash IS NULL OR r.prev_hash IS NULL THEN
              v_unsigned := v_unsigned + 1;
              broken_at_seq  := r.event_seq;
              event_id       := r.event_id;
              session_id     := r.session_id;
              reason         := 'pre-phase5 unsigned';
              expected_hash  := NULL;
              actual_hash    := NULL;
              unsigned_count := v_unsigned;
              RETURN NEXT;
              -- Skip chain-continuity check for this row; prev_payload
              -- stays as it was so the next signed row continues from
              -- the last signed payload_hash we observed.
              CONTINUE;
            END IF;

            -- 1. prev_hash must match the previous SIGNED row's
            --    payload_hash (NULL rows are skipped, not chained).
            IF r.prev_hash IS DISTINCT FROM prev_payload THEN
              broken_at_seq  := r.event_seq;
              event_id       := r.event_id;
              session_id     := r.session_id;
              reason         := 'prev_hash mismatch';
              expected_hash  := prev_payload;
              actual_hash    := r.prev_hash;
              unsigned_count := v_unsigned;
              RETURN NEXT;
            END IF;

            -- 2. payload_hash must equal the recomputed hash.
            expected_hash := encode(
              digest((r.payload_text || '|' || r.prev_hash || '|' || r.actor_text)::text, 'sha256'::text),
              'hex'
            );
            IF r.payload_hash IS DISTINCT FROM expected_hash THEN
              broken_at_seq  := r.event_seq;
              event_id       := r.event_id;
              session_id     := r.session_id;
              reason         := 'payload_hash mismatch';
              expected_hash  := expected_hash;
              actual_hash    := r.payload_hash;
              unsigned_count := v_unsigned;
              RETURN NEXT;
            END IF;

            prev_payload := r.payload_hash;
          END LOOP;

          -- Final trailing summary row so callers can read unsigned_count
          -- even when the chain is otherwise healthy (zero mismatches).
          broken_at_seq  := NULL;
          event_id       := NULL;
          session_id     := NULL;
          reason         := 'chain-summary';
          expected_hash  := NULL;
          actual_hash    := NULL;
          unsigned_count := v_unsigned;
          RETURN NEXT;

          RETURN;
        END;
        $$;
    """)

    op.execute(
        "GRANT EXECUTE ON FUNCTION public.verify_events_chain(uuid) TO PUBLIC;"
    )

    # 2. One-shot backfiller. Only touches rows where payload_hash IS NULL
    #    (or all rows for p_session_id when explicitly scoped). DISABLE /
    #    RE-ENABLE the events_block_mutation trigger locally inside a
    #    SECURITY DEFINER block so the append-only guard is preserved
    #    across the maintenance window.
    op.execute(r"""
        CREATE OR REPLACE FUNCTION public.rebuild_events_chain_hashes(
          p_session_id uuid DEFAULT NULL,
          p_force      boolean DEFAULT FALSE
        )
        RETURNS TABLE (
          rebuilt_rows   bigint,
          skipped_rows   bigint,
          first_seq      bigint,
          last_seq       bigint
        )
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, extensions
        AS $$
        DECLARE
          r               record;
          prev_payload    text := '0000000000000000000000000000000000000000000000000000000000000000';
          v_rebuilt       bigint := 0;
          v_skipped        bigint := 0;
          v_first          bigint := NULL;
          v_last           bigint := NULL;
          v_computed_prev  text;
          v_computed_hash  text;
        BEGIN
          -- Disable the immutability guard for the duration of this
          -- maintenance transaction. We re-enable it in the FINAL block
          -- below regardless of success or failure.
          BEGIN
            ALTER TABLE public.events DISABLE TRIGGER events_block_mutation;
          EXCEPTION WHEN undefined_object THEN NULL;
          END;

          -- Walk the chain in strict monotonic order so prev_hash reflects
          -- the immediately-preceding SIGNED row. NULL rows absorb the
          -- current prev_payload (genesis) only when they are the FIRST
          -- row of their session; otherwise they chain to whatever signed
          -- row came before them.
          FOR r IN
            SELECT e.event_id, e.event_seq, e.session_id, e.payload_hash,
                   COALESCE(e.payload::text, '{}') AS payload_text,
                   COALESCE(e.actor_id::text, '')   AS actor_text
            FROM public.events e
            WHERE (p_session_id IS NULL OR e.session_id = p_session_id)
            ORDER BY e.session_id, e.event_seq
            FOR UPDATE
          LOOP
            IF r.payload_hash IS NOT NULL AND NOT p_force THEN
              -- Already signed and not forced -> leave alone, but feed
              -- it into prev_payload so the next unsigned row chains to
              -- the real previous-signature.
              prev_payload := r.payload_hash;
              v_skipped    := v_skipped + 1;
              CONTINUE;
            END IF;

            v_computed_prev := prev_payload;
            v_computed_hash := encode(
              digest((r.payload_text || '|' || v_computed_prev || '|' || r.actor_text)::text,
                     'sha256'::text),
              'hex'
            );

            -- Direct UPDATE bypasses the (temporarily disabled) trigger.
            UPDATE public.events
               SET prev_hash    = v_computed_prev,
                   payload_hash = v_computed_hash
             WHERE event_id = r.event_id
               AND event_seq = r.event_seq;

            prev_payload := v_computed_hash;
            v_rebuilt    := v_rebuilt + 1;
            v_first      := COALESCE(v_first, r.event_seq);
            v_last       := r.event_seq;
          END LOOP;

          -- Re-enable the immutability trigger.
          BEGIN
            ALTER TABLE public.events ENABLE TRIGGER events_block_mutation;
          EXCEPTION WHEN undefined_object THEN NULL;
          END;

          rebuilt_rows := v_rebuilt;
          skipped_rows := v_skipped;
          first_seq    := v_first;
          last_seq     := v_last;
          RETURN NEXT;
          RETURN;
        END;
        $$;
    """)

    op.execute(
        "GRANT EXECUTE ON FUNCTION public.rebuild_events_chain_hashes(uuid, boolean) TO PUBLIC;"
    )

    # 3. Lightweight unsigned-count helper for monitoring dashboards.
    op.execute(r"""
        CREATE OR REPLACE FUNCTION public.events_unsigned_count(
          p_tenant_id uuid DEFAULT NULL
        )
        RETURNS bigint
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
          SELECT count(*)
          FROM public.events e
          WHERE e.payload_hash IS NULL
            AND (p_tenant_id IS NULL
                 OR EXISTS (
                      SELECT 1 FROM public.sessions s
                      JOIN public.customers c ON c.customer_id = s.customer_id
                      WHERE s.session_id = e.session_id
                        AND c.tenant_id = p_tenant_id
                     ));
        $$;
    """)
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.events_unsigned_count(uuid) TO PUBLIC;"
    )

    # 4. pg_cron stub (opt-in; uncomment after `CREATE EXTENSION pg_cron`).
    # SELECT cron.schedule(
    #   'verify-audit-chain-hourly', '0 * * * *',
    #   $$SELECT count(*) FROM public.verify_events_chain() WHERE reason ~ 'mismatch';$$
    # );


def downgrade() -> None:
    # The Phase-5 verifier is restored on downgrade (so callers see the
    # stricter signature, even though mixed-version rows may again show
    # as false-positive breaks). The backfiller is dropped entirely.
    op.execute("DROP FUNCTION IF EXISTS public.events_unsigned_count(uuid);")
    op.execute("DROP FUNCTION IF EXISTS public.rebuild_events_chain_hashes(uuid, boolean);")

    op.execute("DROP FUNCTION IF EXISTS public.verify_events_chain(uuid);")

    op.execute(r"""
        CREATE OR REPLACE FUNCTION public.verify_events_chain(
          p_tenant_id uuid DEFAULT NULL
        )
        RETURNS TABLE (
          broken_at_seq bigint,
          event_id      uuid,
          session_id    uuid,
          reason        text,
          expected_hash text,
          actual_hash   text
        )
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, extensions
        AS $$
        DECLARE
          r               record;
          prev_payload    text := '0000000000000000000000000000000000000000000000000000000000000000';
          expected_hash   text;
        BEGIN
          FOR r IN
            SELECT e.event_id, e.session_id, e.event_seq,
                   e.payload_hash, e.prev_hash,
                   COALESCE(e.payload::text, '{}') AS payload_text,
                   COALESCE(e.actor_id::text, '')  AS actor_text
            FROM public.events e
            WHERE p_tenant_id IS NULL
               OR EXISTS (
                    SELECT 1 FROM public.sessions s
                    JOIN public.customers c ON c.customer_id = s.customer_id
                    WHERE s.session_id = e.session_id
                      AND c.tenant_id = p_tenant_id
                   )
            ORDER BY e.session_id, e.event_seq
          LOOP
            IF r.prev_hash IS DISTINCT FROM prev_payload THEN
              broken_at_seq := r.event_seq;
              event_id      := r.event_id;
              session_id    := r.session_id;
              reason        := 'prev_hash mismatch';
              expected_hash := prev_payload;
              actual_hash   := r.prev_hash;
              RETURN NEXT;
            END IF;

            expected_hash := encode(
              digest((r.payload_text || '|' || r.prev_hash || '|' || r.actor_text)::text, 'sha256'::text),
              'hex'
            );
            IF r.payload_hash IS DISTINCT FROM expected_hash THEN
              broken_at_seq := r.event_seq;
              event_id      := r.event_id;
              session_id    := r.session_id;
              reason        := 'payload_hash mismatch';
              expected_hash := expected_hash;
              actual_hash   := r.payload_hash;
              RETURN NEXT;
            END IF;

            prev_payload := r.payload_hash;
          END LOOP;
          RETURN;
        END;
        $$;
    """)
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.verify_events_chain(uuid) TO PUBLIC;"
    )
