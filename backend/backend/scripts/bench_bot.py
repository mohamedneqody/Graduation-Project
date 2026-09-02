import httpx, asyncio, time

async def test():
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            'http://localhost:8000/api/v1/ai/chat',
            json={'message': 'هل باراسيتامول دواء مزمن وما سعره؟'}
        )
    elapsed = time.perf_counter() - t0
    reply = r.json()['reply']
    print(f'الوقت: {elapsed:.2f} ث')
    print(f'الرد:\n{reply[:600]}')

asyncio.run(test())
