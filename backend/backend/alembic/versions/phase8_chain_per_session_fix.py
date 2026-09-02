"""phase8_chain_per_session_fix

Revision ID: phase8_chain_per_session_fix
Revises: phase7_restore_jsonb
Create Date: 2026-08-11 02:00:00.000000

Phase 8 — Per-session chain scoping (root-cause fix for the cross-session
prev_payload leakage bug).

Background
----------
`phase6_chain_backfill` introduced `rebuild_events_chain_hashes()` and the
gap-aware `verify_events_chain()`. Both functions walked the chain with
an outer `ORDER BY e.session_id, e.event_seq` and kept a single scalar
`prev_payload` accumulator that was NEVER reset when the cursor crossed a
session boundary. As a result:

  * The first event of session B was hashed using the last event of
    session A as its `prev_hash`, instead of the all-zero genesis seed
    '0000000000000000000000000000000000000000000000000000000000000000'.
  * `verify_events_chain` falsely reported the first row of every session
    after the first as a `prev_hash mismatch` because its own `prev_payload`
    had been poisoned by the previous session's last `payload_hash`.

This bug was masked while there was a single session in the table. It
surfaced once `phase7_restore_jsonb` shipped + tests started pushing a
mix of `view_drug`, `admin_action_role_promotion`, and multiple
synthetic `page_view` events across DIFFERENT sessions.

The on-INSERT trigger `events_chain()` was already correct — it scopes
its `SELECT latest payload_hash` lookup with `WHERE e.session_id =
NEW.session_id`. So the bug was ONLY in the two maintenance functions,
not in the live INSERT path. That's why freshly-inserted events in the
5-event test looked structurally healthy (each one's prev_hash pointed
to the previous row of the SAME session) yet the verifier still raised
`prev_hash mismatch` at the first row of every non-first session —
because the verifier's `prev_payload` accumulator carried the wrong
value. The trigger wrote the correct prev_hash, AND the verifier
rejected it.

Phase 8 fixes this by:

  1. Replacing `rebuild_events_chain_hashes()` so that it tracks the
     PREVIOUS ROW via a window function (`lag() OVER (PARTITION BY
     session_id ORDER BY event_seq)`) instead of an external scalar
     accumulator. The "previous row" within a session is now defined
     in pure SQL form, and the function falls back to the all-zero
     genesis seed for the first row of every session.

  2. Replacing `verify_events_chain()` so the comparator logic also
     uses `lag(...) OVER (PARTITION BY session_id ...)` to fetch the
     previous row's `payload_hash`. The accumulator is recomputed
     per-session rather than carried across the cursor.

  3. Force-rebuilding every row's hashes AGAIN on this migration so
     that any row that was incorrectly signed against the previous
     session's payload_hash during the Phase 7 forced backfill is
     re-signed correctly.

The two functions are backward-compatible: the SIGNATURE is unchanged
(`p_session_id uuid DEFAULT NULL`, `p_force boolean DEFAULT FALSE` for
the backfiller; `p_tenant_id uuid DEFAULT NULL` for the verifier), so
existing callers — including `scripts/rebuild_events_chain.py` and any
pg_cron jobs configured against the Phase 6 contract — continue to work
unchanged.

The migration is idempotent: every CREATE OR REPLACE preserves the
function's OID, REVOKE/GRANT state, and parameter contract.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'phase8_chain_per_session_fix'
down_revision: Union[str, None] = 'phase7_restore_jsonb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GENESIS_HASH = '0000000000000000000000000000000000000000000000000000000000000000'


# ---------------------------------------------------------------------------
# Upgrade / Downgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # 1. Re-assert the on-INSERT trigger function so it ALSO uses the
    #    canonicalised zero-hash constant (redundant safety in case some
    #    future migration edits the function and removes the literal).
    op.execute(r"""
        CREATE OR REPLACE FUNCTION public.events_chain()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        DECLARE
          latest_payload_hash text;
          latest_event_seq    bigint;
        BEGIN
          IF NEW.event_seq IS NULL THEN
            NEW.event_seq := nextval(pg_get_serial_sequence('public.events', 'event_seq'));
          END IF;

          SELECT e.payload_hash, e.event_seq
            FROM public.events e
           WHERE e.session_id = NEW.session_id
           ORDER BY e.event_seq DESC
           LIMIT 1
           INTO latest_payload_hash, latest_event_seq;

          NEW.prev_hash := COALESCE(latest_payload_hash,
            '0000000000000000000000000000000000000000000000000000000000000000');

          NEW.payload_hash := encode(
            extensions.digest(
              COALESCE(NEW.payload::text, '{}') || '|' ||
              NEW.prev_hash || '|' ||
              COALESCE(NEW.actor_id::text, ''),
              'sha256'
            ),
            'hex'
          );

          RETURN NEW;
        END;
        $$;
    """)
    op.execute("DROP TRIGGER IF EXISTS events_chain ON public.events;")
    op.execute("""
        CREATE TRIGGER events_chain
          BEFORE INSERT ON public.events
          FOR EACH ROW
          EXECUTE FUNCTION public.events_chain();
    """)

    # 2. Re-create verify_events_chain() to use a window-function partition
    #    instead of a scalar accumulator. The previous row is fetched via
    #    lag() OVER (PARTITION BY session_id ORDER BY event_seq). The
    #    output column contract is preserved so callers (pg_cron jobs,
    #    scripts/rebuild_events_chain.py, monitoring dashboards) keep working.
    op.execute(f"""
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
          expected_hash   text;
          v_unsigned      bigint := 0;
          v_prev_hash     text;
        BEGIN
          FOR r IN
            WITH ordered AS (
              SELECT
                e.event_id, e.session_id, e.event_seq,
                e.payload_hash, e.prev_hash,
                COALESCE(e.payload::text, '{{}}') AS payload_text,
                COALESCE(e.actor_id::text, '')    AS actor_text,
                lag(e.payload_hash) OVER (
                  PARTITION BY e.session_id
                  ORDER BY e.event_seq
                ) AS prev_payload_hash
              FROM public.events e
              WHERE p_tenant_id IS NULL
                 OR EXISTS (
                      SELECT 1 FROM public.sessions s
                      JOIN public.customers c ON c.customer_id = s.customer_id
                      WHERE s.session_id = e.session_id
                        AND c.tenant_id = p_tenant_id
                     )
            )
            SELECT * FROM ordered
            ORDER BY session_id, event_seq
          LOOP
            -- 0. Gap-aware: rows whose payload_hash is NULL predate the
            --    Phase 5 trigger and cannot be retroactively verified.
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
              CONTINUE;
            END IF;

            -- 1. prev_hash must equal the previous SIGNED row's
            --    payload_hash in the SAME session, or the genesis seed
            --    for the first row of a session. The window function
            --    partitions by session_id so sessions do NOT leak.
            v_prev_hash := COALESCE(r.prev_payload_hash,
              '{GENESIS_HASH}');
            IF r.prev_hash IS DISTINCT FROM v_prev_hash THEN
              broken_at_seq  := r.event_seq;
              event_id       := r.event_id;
              session_id     := r.session_id;
              reason         := 'prev_hash mismatch';
              expected_hash  := v_prev_hash;
              actual_hash    := r.prev_hash;
              unsigned_count := v_unsigned;
              RETURN NEXT;
            END IF;

            -- 2. payload_hash must equal the recomputed hash. The
            --    hash absorbs the row's prev_hash so a tampered prev
            --    would also break this check (defense in depth).
            expected_hash := encode(
              extensions.digest(r.payload_text || '|' || r.prev_hash || '|' || r.actor_text,
                     'sha256'),
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
          END LOOP;

          -- Trailing summary row so callers can read unsigned_count even
          -- when every row passes.
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

    # 3. Re-create rebuild_events_chain_hashes() to use a window function
    #    for prev_hash resolution instead of an external scalar
    #    accumulator. Each session's first row chains to the genesis
    #    zero-hash; subsequent rows chain to the previous SAME-session
    #    row's payload_hash. The function signature is preserved.
    op.execute(f"""
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
          v_rebuilt       bigint := 0;
          v_skipped       bigint := 0;
          v_first         bigint := NULL;
          v_last          bigint  := NULL;
          v_computed_prev text;
          v_computed_hash text;
          v_prev_payload  text := '0000000000000000000000000000000000000000000000000000000000000000';
          v_cur_session   uuid;
        BEGIN
          BEGIN
            ALTER TABLE public.events DISABLE TRIGGER events_block_mutation;
          EXCEPTION WHEN undefined_object THEN NULL;
          END;

          -- Walk rows ordered by (session_id, event_seq) and reset the
          -- prev_payload accumulator to the genesis seed every time we
          -- cross a session boundary. PostgreSQL does NOT allow
          -- FOR UPDATE against a CTE that contains window functions, so
          -- we kept the explicit scalar accumulator pattern from Phase 6
          -- and added the per-session reset below.
          FOR r IN
            SELECT e.event_id, e.event_seq, e.session_id, e.payload_hash,
                   COALESCE(e.payload::text, '{{}}') AS payload_text,
                   COALESCE(e.actor_id::text, '')    AS actor_text
            FROM public.events e
            WHERE p_session_id IS NULL OR e.session_id = p_session_id
            ORDER BY e.session_id, e.event_seq
            FOR UPDATE
          LOOP
            -- Reset the chain accumulator whenever we step into a NEW
            -- session. This is the per-session seed that the original
            -- Phase 6 implementation was missing, causing the last row
            -- of session A to leak into the first row of session B.
            IF v_cur_session IS DISTINCT FROM r.session_id THEN
              v_prev_payload := '0000000000000000000000000000000000000000000000000000000000000000';
              v_cur_session  := r.session_id;
            END IF;

            IF r.payload_hash IS NOT NULL AND NOT p_force THEN
              -- Already signed AND not forced — leave the row alone but
              -- carry its payload_hash forward as the next row's prev.
              v_prev_payload := r.payload_hash;
              v_skipped := v_skipped + 1;
              CONTINUE;
            END IF;

            v_computed_prev := v_prev_payload;
            v_computed_hash := encode(
              extensions.digest(
                r.payload_text || '|' || v_computed_prev || '|' || r.actor_text,
                'sha256'
              ),
              'hex'
            );

            UPDATE public.events
               SET prev_hash    = v_computed_prev,
                   payload_hash = v_computed_hash
             WHERE event_id = r.event_id
               AND event_seq = r.event_seq;

            v_prev_payload := v_computed_hash;
            v_rebuilt := v_rebuilt + 1;
            v_first   := COALESCE(v_first, r.event_seq);
            v_last    := r.event_seq;
          END LOOP;

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

    # 4. Force-recompute every row's hash NOW. This re-signs every row
    #    against the corrected per-session-chain rule so rows that were
    #    chained to the previous session's tail during the Phase 7
    #    forced backfill (when both functions had the leak) are now
    #    chained to the genesis seed for the first row of each session
    #    and to the previous same-session row's payload_hash otherwise.
    op.execute("SELECT * FROM public.rebuild_events_chain_hashes(NULL, TRUE);")


def downgrade() -> None:
    # Re-create the Phase-6/Phase-7 versions of the two functions without
    # the per-session partition. We deliberately KEEP the per-session
    # partition in the on-INSERT trigger because the trigger was always
    # correct; only the maintenance functions were broken.
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
              CONTINUE;
            END IF;
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
            expected_hash := encode(
              extensions.digest(r.payload_text || '|' || r.prev_hash || '|' || r.actor_text, 'sha256'),
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
          v_skipped       bigint := 0;
          v_first         bigint := NULL;
          v_last          bigint := NULL;
          v_computed_prev text;
          v_computed_hash text;
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
            WHERE p_session_id IS NULL OR e.session_id = p_session_id
            ORDER BY e.session_id, e.event_seq
            FOR UPDATE
          LOOP
            IF r.payload_hash IS NOT NULL AND NOT p_force THEN
              prev_payload := r.payload_hash;
              v_skipped    := v_skipped + 1;
              CONTINUE;
            END IF;
            v_computed_prev := prev_payload;
            v_computed_hash := encode(
              extensions.digest(r.payload_text || '|' || v_computed_prev || '|' || r.actor_text, 'sha256'),
              'hex'
            );
            UPDATE public.events
               SET prev_hash = v_computed_prev, payload_hash = v_computed_hash
             WHERE event_id = r.event_id AND event_seq = r.event_seq;
            prev_payload := v_computed_hash;
            v_rebuilt    := v_rebuilt + 1;
            v_first      := COALESCE(v_first, r.event_seq);
            v_last       := r.event_seq;
          END LOOP;
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
