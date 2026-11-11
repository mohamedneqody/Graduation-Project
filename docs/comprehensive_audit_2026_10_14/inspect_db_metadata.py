"""Read-only catalog inspection. Does not retrieve customer or clinical rows."""
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT / 'AI-COS-Pharmacy' / 'backend')
sys.path.insert(0, str(Path.cwd()))
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={'timeout': 15})
    result = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text('SET TRANSACTION READ ONLY'))
            await conn.execute(text("SET LOCAL statement_timeout = '15000'"))
            queries = {
                'role': 'SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = current_user',
                'tables': "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, pg_get_userbyid(c.relowner)=current_user AS app_is_owner FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.relname",
                'policies': "SELECT tablename, policyname, permissive, roles::text, cmd, qual, with_check FROM pg_policies WHERE schemaname='public' ORDER BY tablename,policyname",
                'indexes': "SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY tablename,indexname",
                'triggers': "SELECT event_object_table,trigger_name,event_manipulation,action_statement FROM information_schema.triggers WHERE trigger_schema='public' ORDER BY event_object_table,trigger_name",
                'constraints': "SELECT c.conrelid::regclass::text AS table_name, c.conname, c.contype, pg_get_constraintdef(c.oid) AS definition FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' ORDER BY table_name,c.conname",
                'revision': 'SELECT version_num FROM alembic_version',
            }
            for name, sql in queries.items():
                result[name] = [dict(r) for r in (await conn.execute(text(sql))).mappings().all()]
            await conn.rollback()
    except Exception as exc:
        result['error_type'] = type(exc).__name__
    finally:
        await engine.dispose()
    target = Path(__file__).with_name('db_metadata.json')
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({'role':result.get('role'), 'revision':result.get('revision'),
       'tables':len(result.get('tables',[])), 'policies':len(result.get('policies',[])),
       'error_type':result.get('error_type')}, ensure_ascii=False))

asyncio.run(main())
