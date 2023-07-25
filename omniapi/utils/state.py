import asyncio
from dataclasses import dataclass
from typing import Optional

import aiohttp_retry


@dataclass
class ClientState:
    """
    ClientState is a dataclass representing the state of a client in an asynchronous context.

    Attributes:
        client (aiohttp_retry.RetryClient): A RetryClient instance from the aiohttp_retry library.
            This is a client which automatically retries failed requests.
        api_keys_queue (Optional[asyncio.Queue]): An asyncio Queue instance holding API keys.
            It can be None, if no API keys are needed.
        semaphores (dict): A dictionary containing semaphores for each API key.
            Semaphores are used for limiting the number of simultaneous requests for each API key.
        last_request_time (dict): A dictionary keeping track of the last request time for each API key.
        wait_time (float): The amount of time to wait between requests.
    """
    client: aiohttp_retry.RetryClient
    api_keys_queue: Optional[asyncio.Queue]
    semaphores: dict
    last_request_time: dict
    wait_time: float
