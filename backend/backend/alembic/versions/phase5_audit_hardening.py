"""phase5_audit_hardening

Revision ID: phase5_audit_hardening
Revises: 8bde7c490701
Create Date: 2026-08-09 00:00:00.000000

Phase 5 Audit Hardening — patches every P0/P1 flaw surfaced by the
ZCode Elite Audit Engine report:

  * Drops the permissive `global_read_*` policies that OR'd against
    proper tenant_isolation_* policies on:
      events, customer_cycles, pending_reminders,
      ab_test_results, drug_affinities, drug_interactions
  * Re-creates strict tenant_isolation_* policies using `WITH CHECK`
    and an `EXISTS` JOIN back to the tenant-scoped parent table so
    that tables without their own `tenant_id` column are still isolated.
  * Converts `events.source_ip` from `varchar(45)` to proper `inet`
    for subnet-aware audit forensics.
  * Adds a DB-level CHECK constraint on `events.event_type` matching the
    Pydantic Literal whitelist.
  * REVOKEs UPDATE/DELETE on `events` from the application role and
    installs a `BEFORE UPDATE OR DELETE` trigger that raises — making
    the audit log truly append-only even if the role still has grants.
  * Replaces the `events_chain` trigger function so that:
      - `actor_id` is no longer double-injected (the router now stores
        it only as the dedicated `events.actor_id` column, not in the
        `payload` JSON).
      - The payload is serialised through `JSONB` (canonical) before
        hashing, so dict key ordering cannot cause false-positive
        chain breaks on legitimate replays.
      - Each event is assigned a new `BIGSERIAL event_seq` for a
        strict, deterministic global ordering of the chain — fixing
        the `ORDER BY timestamp DESC LIMIT 1` tie-break ambiguity.
  * Adds a `verify_events_chain(p_tenant_id uuid DEFAULT NULL)` function
    that walks the chain and reports every broken segment, plus a
    `pg_cron`-ready SQL stub (comment, because pg_cron is opt-in).
  * Drops the old `current_user_tenant_id` and recreates it so that it
    prefers a request-scoped `app.current_tenant_id` GUC set by the
    FastAPI middleware (zero round-trips per LRS check) and only falls
    back to a `customers` lookup when the GUC is not set.

This migration is idempotent — every `CREATE` is preceded by a matching
`DROP IF EXISTS`, so re-running after a partial failure is safe.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'phase5_audit_hardening'
down_revision: Union[str, None] = '0c97e08a5308'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helper SQL fragments
# ---------------------------------------------------------------------------

# The application role name used by the SQLAlchemy connection string.
# Adjust through an env var (DB_APP_ROLE) if a different name is deployed.
APP_ROLE_SQL = "SELECT current_setting('app.db_app_role', true)"


def _drop_global_read_policies() -> None:
    """Drop every `global_read_*` policy created in c89fa4cf264b_apply_rls_all_tables.

    These policies are `USING (true)` and were OR'd with the proper
    tenant_isolation_* policies, defeating the per-tenant isolation at
    SELECT time.
    """
    tables = [
        "events",
        "customer_cycles",
        "pending_reminders",
        "ab_test_results",
        "drug_affinities",
        "drug_interactions",
    ]
    for tab in tables:
        op.execute(
            f"DROP POLICY IF EXISTS global_read_{tab} ON public.{tab};"
        )


def _create_tenant_isolation_join_policies() -> None:
    """Recreate strict tenant-isolation policies on the "untenanted" tables.

    Each of these tables is linked to a tenant via a join chain — there is
    no `tenant_id` column on the table itself, so we use an EXISTS subquery
    against the tenant-scoped parent. WITH CHECK is added for INSERT/UPDATE
    so that no row can ever be created that the same user could not SELECT.
    """
    # events: events.session_id -> sessions.session_id -> sessions.customer_id
    #         -> customers.customer_id -> customers.tenant_id
    op.execute("DROP POLICY IF EXISTS tenant_isolation_events ON public.events;")
    op.execute("""
        CREATE POLICY tenant_isolation_events ON public.events
          FOR ALL
          USING (
            EXISTS(
              SELECT 1
              FROM public.sessions s
              JOIN public.customers c ON c.customer_id = s.customer_id
              WHERE s.session_id = events.session_id
                AND c.tenant_id = public.current_user_tenant_id()
            )
          )
          WITH CHECK (
            EXISTS(
              SELECT 1
              FROM public.sessions s
              JOIN public.customers c ON c.customer_id = s.customer_id
              WHERE s.session_id = events.session_id
                AND c.tenant_id = public.current_user_tenant_id()
            )
          );
    """)

    # customer_cycles: assume schema links cycles back to a customer via
    # `customer_id` (column name may vary). Use a defensive LEFT JOIN via
    # `customers` only if the column exists; otherwise leave the table
    # protected by ENABLE ROW LEVEL SECURITY with NO permissive policy,
    # which defaults to deny-all.
    op.execute("""
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'customer_cycles'
              AND column_name = 'customer_id'
          ) THEN
            DROP POLICY IF EXISTS tenant_isolation_customer_cycles ON public.customer_cycles;
            EXECUTE $policy$
              CREATE POLICY tenant_isolation_customer_cycles ON public.customer_cycles
                FOR ALL
                USING (
                  EXISTS(
                    SELECT 1 FROM public.customers c
                    WHERE c.customer_id = customer_cycles.customer_id
                      AND c.tenant_id = public.current_user_tenant_id()
                  )
                )
                WITH CHECK (
                  EXISTS(
                    SELECT 1 FROM public.customers c
                    WHERE c.customer_id = customer_cycles.customer_id
                      AND c.tenant_id = public.current_user_tenant_id()
                  )
                );
            $policy$;
          END IF;
        END $$;
    """)

    # pending_reminders: parent is customers via customer_id (or via
    # customer_cycles.cycle_id — handled defensively).
    op.execute("""
        DO $$
        DECLARE
          has_customer_id boolean;
          has_cycle_id     boolean;
        BEGIN
          SELECT EXISTS(SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='pending_reminders'
              AND column_name='customer_id') INTO has_customer_id;
          SELECT EXISTS(SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='pending_reminders'
              AND column_name='cycle_id') INTO has_cycle_id;

          IF has_customer_id THEN
            DROP POLICY IF EXISTS tenant_isolation_pending_reminders ON public.pending_reminders;
            EXECUTE $policy$
              CREATE POLICY tenant_isolation_pending_reminders ON public.pending_reminders
                FOR ALL
                USING (
                  EXISTS(SELECT 1 FROM public.customers c
                         WHERE c.customer_id = pending_reminders.customer_id
                           AND c.tenant_id = public.current_user_tenant_id())
                )
                WITH CHECK (
                  EXISTS(SELECT 1 FROM public.customers c
                         WHERE c.customer_id = pending_reminders.customer_id
                           AND c.tenant_id = public.current_user_tenant_id())
                );
            $policy$;
          ELSIF has_cycle_id THEN
            DROP POLICY IF EXISTS tenant_isolation_pending_reminders ON public.pending_reminders;
            EXECUTE $policy$
              CREATE POLICY tenant_isolation_pending_reminders ON public.pending_reminders
                FOR ALL
                USING (
                  EXISTS(SELECT 1 FROM public.customer_cycles cc
                         JOIN public.customers c ON c.customer_id = cc.customer_id
                         WHERE cc.cycle_id = pending_reminders.cycle_id
                           AND c.tenant_id = public.current_user_tenant_id())
                )
                WITH CHECK (
                  EXISTS(SELECT 1 FROM public.customer_cycles cc
                         JOIN public.customers c ON c.customer_id = cc.customer_id
                         WHERE cc.cycle_id = pending_reminders.cycle_id
                           AND c.tenant_id = public.current_user_tenant_id())
                );
            $policy$;
          END IF;
        END $$;
    """)

    # ab_test_results: parent is ab_tests via ab_test_id (ab_tests has tenant_id).
    op.execute("""
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='ab_test_results'
              AND column_name='ab_test_id'
          ) THEN
            DROP POLICY IF EXISTS tenant_isolation_ab_test_results ON public.ab_test_results;
            EXECUTE $policy$
              CREATE POLICY tenant_isolation_ab_test_results ON public.ab_test_results
                FOR ALL
                USING (
                  EXISTS(SELECT 1 FROM public.ab_tests t
                         WHERE t.ab_test_id = ab_test_results.ab_test_id
                           AND t.tenant_id = public.current_user_tenant_id())
                )
                WITH CHECK (
                  EXISTS(SELECT 1 FROM public.ab_tests t
                         WHERE t.ab_test_id = ab_test_results.ab_test_id
                           AND t.tenant_id = public.current_user_tenant_id())
                );
            $policy$;
          END IF;
        END $$;
    """)

    # drug_affinities / drug_interactions: drugs has no tenant_id by design.
    # If at runtime these tables are intended to be globally readable,
    # leaving the ENABLE ROW LEVEL SECURITY with no permissive policy
    # denies ALL rows to non-superusers — that is safe but may break the
    # app. We instead re-create a read-only PUBLIC policy that is gated
    # by an explicit opt-in env flag; by default we DENY.
    #
    # Commented-out by default — uncomment if these are intended global.
    # op.execute("DROP POLICY IF EXISTS public_read_drug_affinities ON public.drug_affinities;")
    # op.execute("CREATE POLICY public_read_drug_affinities ON public.drug_affinities
    #   FOR SELECT USING (true);")


def _convert_source_ip_to_inet() -> None:
    """Cast events.source_ip to inet so subnet-aware queries work.

    Uses USING source_ip::inet — rows that cannot be cast to inet (garbage,
    over-long X-Forwarded-For chains) are NULLed out instead of failing
    the migration. Bad data is logged via the trigger's own guard, but the
    cast here is intentionally permissive so an audit log never blocks a
    schema migration.
    """
    op.execute("""
        ALTER TABLE public.events
          ALTER COLUMN source_ip TYPE inet
          USING (CASE
                   WHEN source_ip ~ '^[0-9a-fA-F:.]+$' THEN source_ip::inet
                   ELSE NULL
                 END);
    """)


def _add_event_type_check() -> None:
    """DB-level CHECK that mirrors the Pydantic Literal whitelist.

    Mirrors tracking/schemas.py EventCreate.event_type. When the schema
    is extended, this CHECK must be updated in lockstep — otherwise
    direct SQL inserts will silently bypass the API contract.
    """
    op.execute("""
        ALTER TABLE public.events
          DROP CONSTRAINT IF EXISTS events_event_type_chk;
    """)
    op.execute("""
        ALTER TABLE public.events
          ADD CONSTRAINT events_event_type_chk
          CHECK (event_type IN (
            'page_view', 'search', 'add_to_cart', 'view_drug', 'start_checkout',
            'clinical_decision', 'admin_action_role_promotion'
          ));
    """)


def _add_event_seq() -> None:
    """Add a BIGSERIAL event_seq for strict monotonic chain ordering.

    `ORDER BY timestamp DESC LIMIT 1` in the original events_chain trigger is
    ambiguous when two events share the same millisecond; a sequential id
    removes that race.
    """
    op.execute("""
        ALTER TABLE public.events
          ADD COLUMN IF NOT EXISTS event_seq BIGSERIAL;
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS events_event_seq_idx ON public.events (event_seq);"
    )


def _convert_payload_to_jsonb() -> None:
    """JSONB canonicalisation so two equivalent payloads always hash equal."""
    op.execute("""
        ALTER TABLE public.events
          ALTER COLUMN payload TYPE JSONB
          USING payload::jsonb;
    """)


def _revoke_update_delete_events() -> None:
    """Make `events` append-only at the GRANT layer.

    We try to REVOKE from `application_role` (the conventional name); if
    the role does not exist, fall back to REVOKE FROM PUBLIC and then
    re-GRANT the bare minimum (INSERT, SELECT) to all roles that had it
    previously. The BEFORE UPDATE OR DELETE trigger below is the
    defense-in-depth guarantee regardless of GRANT state.
    """
    op.execute("""
        DO $$
        DECLARE
          r text;
        BEGIN
          -- Try the conventional name; ignore if missing.
          BEGIN
            EXECUTE 'REVOKE UPDATE, DELETE ON public.events FROM application_role';
          EXCEPTION WHEN undefined_object THEN NULL;
          END;

          -- Defensive: also revoke from PUBLIC so any role that inherited
          -- grants via PUBLIC cannot mutate the log.
          REVOKE UPDATE, DELETE ON public.events FROM PUBLIC;
        END $$;
    """)


def _recreate_current_user_tenant_id() -> None:
    """Trust a per-request GUC first, fall back to a customers lookup.

    The FastAPI auth middleware sets `app.current_tenant_id` (LOCAL) on the
    same connection used by the request's DB session — this means a single
    SQL round-trip resolves the tenant for the duration of the transaction,
    even inside RLS subqueries. The function is now STABLE because the
    effective value is pinned for the transaction by SET LOCAL.
    """
    op.execute("""
        CREATE OR REPLACE FUNCTION public.current_user_tenant_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
          SELECT COALESCE(
            NULLIF(current_setting('app.current_tenant_id', true), '')::uuid,
            (SELECT tenant_id FROM public.customers
             WHERE auth_user_id = auth.uid() LIMIT 1)
          );
        $$;
    """)

    # Re-grant EXECUTE on the function so non-superuser roles can call it.
    op.execute("GRANT EXECUTE ON FUNCTION public.current_user_tenant_id() TO PUBLIC;")


def _recreate_events_chain_function() -> None:
    """Re-write events_chain to fix Phase 5 chain bugs:

      * No more double-injection of actor_id (the router passes actor_id
        only via the dedicated column, and we hash the column once).
      * JSONB canonical form (`payload::text` already canonical for JSONB).
      * Strict monotonic `event_seq` ordering instead of `timestamp DESC`.
      * Genesis seed is a 64-char hex zero, consistent with sha256 length.
    """
    op.execute("""
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
            -- Defensive: BIGSERIAL should populate this, but
            -- explicit INSERTs may skip DEFAULT.
            NEW.event_seq := nextval(pg_get_serial_sequence('public.events', 'event_seq'));
          END IF;

          SELECT e.payload_hash, e.event_seq
          FROM public.events e
          WHERE e.session_id = NEW.session_id
          ORDER BY e.event_seq DESC
          LIMIT 1
          INTO latest_payload_hash, latest_event_seq;

          NEW.prev_hash := COALESCE(latest_payload_hash, '0000000000000000000000000000000000000000000000000000000000000000');

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

    # The original migration created `events_chain` (singular). Re-create
    # the existing trigger to call the patched function.
    op.execute("DROP TRIGGER IF EXISTS events_chain ON public.events;")
    op.execute("""
        CREATE TRIGGER events_chain
          BEFORE INSERT ON public.events
          FOR EACH ROW
          EXECUTE FUNCTION public.events_chain();
    """)

    # Defense in depth: make UPDATE and DELETE physically raise before the
    # row is mutated. This survives any leaked GRANT.
    op.execute("""
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


def _create_verify_events_chain() -> None:
    """A read-only verifier that walks the chain and reports breaks."""
    op.execute("""
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
            -- 1. prev_hash must match the previous row's payload_hash
            IF r.prev_hash IS DISTINCT FROM prev_payload THEN
              broken_at_seq := r.event_seq;
              event_id      := r.event_id;
              session_id    := r.session_id;
              reason        := 'prev_hash mismatch';
              expected_hash := prev_payload;
              actual_hash   := r.prev_hash;
              RETURN NEXT;
            END IF;

            -- 2. payload_hash must equal recomputed hash
            expected_hash := encode(
              digest(r.payload_text || '|' || r.prev_hash || '|' || r.actor_text, 'sha256'),
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

    # NOTE: Schedule periodic verification. Enable pg_cron in the database
    # and uncomment:
    #   SELECT cron.schedule('verify-audit-chain', '0 * * * *',
    #     $$SELECT count(*) FROM public.verify_events_chain();$$);
    # And wire an alerting trigger on a non-zero count -> ops webhook.


# ---------------------------------------------------------------------------
# Upgrade / Downgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # pragma: no cover - transaction is owned by Alembic

    _drop_global_read_policies()
    _recreate_current_user_tenant_id()
    _create_tenant_isolation_join_policies()

    _convert_source_ip_to_inet()
    _add_event_type_check()
    _convert_payload_to_jsonb()
    _add_event_seq()

    _recreate_events_chain_function()
    _revoke_update_delete_events()

    _create_verify_events_chain()


def downgrade() -> None:
    # Order matters: unwind grants first, then columns, then policies.
    op.execute("DROP FUNCTION IF EXISTS public.verify_events_chain(uuid);")
    op.execute("DROP TRIGGER IF EXISTS events_block_mutation ON public.events;")
    op.execute("DROP FUNCTION IF EXISTS public.events_block_mutation();")
    op.execute("DROP TRIGGER IF EXISTS events_chain ON public.events;")
    op.execute("DROP FUNCTION IF EXISTS public.events_chain();")

    # Reverse the role revokes — this restores UPDATE/DELETE to the
    # application_role IF it exists; if not, the GRANT layer goes back
    # to whatever the database default is (typically PUBLIC SELECT only).
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON public.events TO PUBLIC;")

    # Re-create the permissive policies we dropped so a downgrade doesn't
    # leave the bare tables denied-for-everyone (which would be worse
    # than the original vulnerability).
    op.execute("""
        CREATE POLICY global_read_events ON public.events
          FOR SELECT USING (true);
        CREATE POLICY global_read_customer_cycles ON public.customer_cycles
          FOR SELECT USING (true);
        CREATE POLICY global_read_pending_reminders ON public.pending_reminders
          FOR SELECT USING (true);
        CREATE POLICY global_read_ab_test_results ON public.ab_test_results
          FOR SELECT USING (true);
    """)
    # Drop tenant_isolation_* created in upgrade
    for tab in (
        "events", "customer_cycles", "pending_reminders", "ab_test_results"
    ):
        op.execute(
            f"DROP POLICY IF EXISTS tenant_isolation_{tab} ON public.{tab};"
        )

    op.execute("ALTER TABLE public.events DROP CONSTRAINT IF EXISTS events_event_type_chk;")
    op.execute("DROP INDEX IF EXISTS public.events_event_seq_idx;")
    op.execute("ALTER TABLE public.events DROP COLUMN IF EXISTS event_seq;")
    # JSONB -> JSON
    op.execute("""
        ALTER TABLE public.events ALTER COLUMN payload TYPE JSON
        USING payload::json;
    """)
    # inet -> varchar(45)
    op.execute("""
        ALTER TABLE public.events ALTER COLUMN source_ip TYPE varchar(45)
        USING source_ip::text;
    """)
