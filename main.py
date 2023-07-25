import asyncio
from aiohttp import ClientSession
from omniapi import APIClient
import time


async def request(session, url: str):
    async with session.request("GET", url) as response:
        await response.json()


async def run():
    t = time.time()
    async with APIClient(max_requests_per_interval=5) as client:
        await client.get([f'https://pokeapi.co/api/v2/pokemon/{i}' for i in range(1, 5)])
    print(time.time() - t)

    # t = time.time()
    # session = ClientSession()
    # await asyncio.gather(*[asyncio.create_task(
    #     request(session, f'https://pokeapi.co/api/v2/pokemon/{i}')) for i in range(1, 1000)])
    # await session.close()
    # print(time.time() - t)

asyncio.run(run())
