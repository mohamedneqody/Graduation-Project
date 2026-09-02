import asyncio, asyncpg
async def main():
    conn = await asyncpg.connect('postgresql://postgres.quhfheudhewxqmvxwjij:010704613318686@aws-0-eu-central-1.pooler.supabase.com:5432/postgres')
    rows = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    for r in rows:
        print(r['table_name'])
    await conn.close()
asyncio.run(main())
