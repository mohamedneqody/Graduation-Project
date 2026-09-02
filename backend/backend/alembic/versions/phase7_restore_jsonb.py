"""phase7_restore_jsonb

Revision ID: phase7_restore_jsonb
Revises: b7a790f21e4b
Create Date: 2026-08-11 01:00:00.000000

Phase 7 — Restore JSONB canonical audit chain.

Background
----------
Migration `b7a790f21e4b_add_tenant_settings` was auto-generated while the
ORM model `app/models/session.py` still declared `events.payload` as
generic SQLAlchemy `JSON` (= Postgres `json`). Alembic therefore dutifully
emitted:

    op.alter_column('events', 'payload',
                    existing_type=postgresql.JSONB(astext_type=sa.Text()),
                    type_=sa.JSON(),
                    existing_nullable=True)

…silently regressing the column from `jsonb` to `json`. Because the
`events_chain()` trigger hashes `COALESCE(NEW.payload::text, '{}')`, and
the text representation of `json` is NOT canonical (key order is the
insertion order, no whitespace normalisation), this broke three things at
once:

  1. The immutability hash chain started producing non-canonical
     `payload_hash` values for any event inserted after the regression,
     so `verify_events_chain()` reported `prev_hash mismatch` at the
     boundary between pre-regression (JSONB) and post-regression (json)
     rows. The chain was cryptographically broken for real.

  2. asyncpg, the asyncpg DBAPI used by SQLAlchemy's async engine,
     prepares INSERT statements with `$4::JSON`. When the prepared
     statement is reused on a second request whose actual column type
     is `jsonb`, asyncpg raises
     `DatatypeMismatchError: type of parameter 21 (json) does not match
     that when preparing the plan (jsonb)` and the API returns HTTP 500
     for every event POST other than the first on a connection. This is
     a connection-sticky bug — first request succeeds, second 500s.

  3. The GIN index that `tenant_isolation_events` could use for JSONB
     path filters silently disappeared.

Phase 7 fixes all three by:

  * Restoring `events.payload` to `JSONB` (so `payload::text` is again
    canonical Syscache representation).
  * Re-asserting `events_chain()` trigger function with the exact same
    hashing input formula as Phase 5 — so any row whose `payload_hash`
    was computed under the broken `json` canonical form is now RELATIVE
    to the canonical JSONB form. We therefore also…
  * Invoking `rebuild_events_chain_hashes(NULL, TRUE)` immediately after
    the type alteration so EVERY existing row's `prev_hash` and
    `payload_hash` are recomputed against the uniform canonical form, and
    `verify_events_chain()` returns zero mismatches.

The migration is idempotent — every CREATE/DROP is guarded.

NOTE: This migration intentionally DOES NOT touch the `tenant_settings`
table or the `contact_messages` schema fixes introduced by `b7a790f`.
Those are unrelated features and remain in force.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'phase7_restore_jsonb'
down_revision: Union[str, None] = 'b7a790f21e4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Upgrade / Downgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # 1. Restore events.payload to JSONB. The `USING payload::jsonb` cast
    #    re-canonicalises every row's payload automatically — Postgres
    #    parses the json text and re-emits it as JSONB canonical form.
    op.execute("""
        ALTER TABLE public.events
          ALTER COLUMN payload TYPE JSONB
          USING payload::jsonb;
    """)

    # 2. Re-assert the events_chain trigger function so that the hash
    #    formula is identical to Phase 5 (we re-emit the exact same body
    #    here so a future migration that mutates the function cannot
    #    retroactively change hashes computed in this migration's frames).
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
            digest(
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

    # Re-create the trigger if it was somehow dropped.
    op.execute("DROP TRIGGER IF EXISTS events_chain ON public.events;")
    op.execute("""
        CREATE TRIGGER events_chain
          BEFORE INSERT ON public.events
          FOR EACH ROW
          EXECUTE FUNCTION public.events_chain();
    """)

    # 3. Re-assert the block-mutation trigger (defense in depth).
    op.execute(r"""
        CREATE OR REPLACE FUNCTION public.events_block_mutation()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        BEGIN
          RAISE EXCEPTION 'public.events is append-only: UPDATE/DELETE is forbidden (HIPAA 45 CFR 164.312(c)(1)).';
        END;
        $$;
    """)
    op.execute("DROP TRIGGER IF EXISTS events_block_mutation ON public.events;")
    op.execute("""
        CREATE TRIGGER events_block_mutation
          BEFORE UPDATE OR DELETE ON public.events
          FOR EACH ROW
          EXECUTE FUNCTION public.events_block_mutation();
    """)

    # 4. Force-recompute every row's hash so the chain is uniformly
    #    canonicalised to JSONB. This is idempotent — recomputing on an
    #    already-clean row yields the same hash. We pass TRUE so the
    #    function does not skip already-signed rows: any row signed under
    #    the json canonical form will be re-signed here, and the chain
    #    will re-link cleanly because each row's prev_hash re-stitches to
    #    the freshly computed prior payload_hash.
    op.execute("SELECT * FROM public.rebuild_events_chain_hashes(NULL, TRUE);")


def downgrade() -> None:
    # We do NOT revert the type alteration — leaving the column as `json`
    # would silently re-introduce the bug. Downgrade intentionally only
    # re-emits the trigger functions defensively so the system is left
    # in a stable state if alembic is forced to downgrade.
    op.execute(r"""
        CREATE OR REPLACE FUNCTION public.events_chain()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        DECLARE
          latest_payload_hash text;
        BEGIN
          IF NEW.event_seq IS NULL THEN
            NEW.event_seq := nextval(pg_get_serial_sequence('public.events', 'event_seq'));
          END IF;
          SELECT e.payload_hash FROM public.events e
           WHERE e.session_id = NEW.session_id
           ORDER BY e.event_seq DESC LIMIT 1 INTO latest_payload_hash;
          NEW.prev_hash := COALESCE(latest_payload_hash,
            '0000000000000000000000000000000000000000000000000000000000000000');
          NEW.payload_hash := encode(digest(
            COALESCE(NEW.payload::text, '{}') || '|' || NEW.prev_hash || '|' ||
            COALESCE(NEW.actor_id::text, ''), 'sha256'), 'hex');
          RETURN NEW;
        END;
        $$;
    """)
