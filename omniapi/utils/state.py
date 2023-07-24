import asyncio
from dataclasses import dataclass
from typing import Optional

import aiohttp_retry


@dataclass
class ClientState:
    client: aiohttp_retry.RetryClient
    api_keys_queue: Optional[asyncio.Queue]
    semaphores: dict
    last_request_time: dict
    wait_time: float
