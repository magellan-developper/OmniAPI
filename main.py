import asyncio
import time
from typing import Any

from omniapi import APIClient, Result


class TestClient(APIClient):
    def setup_request(self, url: str, headers: dict, data: dict, api_key: str):
        pass

    async def request_callback(self, result: Result, setup_info):
        result_type, content = self.get_result_content(result)
        print(len(content))
async def request(session, url: str):
    async with session.request("GET", url) as response:
        await response.json()


async def run():
    t = time.time()
    async with APIClient(max_requests_per_interval=5) as client:
        await client.get([f'https://pokeapi.co/api/v2/pokemon/{i}' for i in range(1, 5)])
    print(time.time() - t)

asyncio.run(run())