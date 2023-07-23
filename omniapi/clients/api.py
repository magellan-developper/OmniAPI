
import asyncio
import hashlib
import json
import mimetypes
import time
import typing
import os
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, unquote_to_bytes
from enum import Enum, auto
from dataclasses import dataclass
import aiofiles
import aiohttp
import aiohttp_retry
import structlog
from tqdm.asyncio import tqdm_asyncio

from omniapi.services.api.base.config import BaseClientConfig, FileNameMode

structlog.configure(processors=[structlog.processors.JSONRenderer()])





class APIClient(BaseClient):
    def __init__(self, base_url: str, config: BaseClientConfig, api_keys: Optional[list[str]] = None):
        super().__init__(base_url, config, api_keys=api_keys)

    async def _make_request_setup(self):
        api_key = await self.api_keys_queue.get() if self.api_keys_queue is not None else None
        if api_key is not None:
            assert isinstance(self.semaphores, dict)
            await self._sleep_for_rate_limit(api_key)
            await self.semaphores[api_key].acquire()
            self.api_keys_queue.put_nowait(api_key)
        else:
            await self._sleep_for_rate_limit()
        return api_key

    @staticmethod
    async def fetch_content(result: Result):
        headers = result.response.headers
        file_type = headers['Content-Type'].split(';')[0]
        if file_type == 'text/plain':
            return await result.text()
        elif file_type == 'application/json':
            return await result.json()
        else:
            return await result.download()

    def setup_request(self, endpoint, headers, params, data, api_key):
        if self.config.api_key_field is not None:
            params[self.config.api_key_field] = api_key

    async def process_request_callback(self, result_type: ResultType, content):
        pass

    async def request_callback(self, result: Result, endpoint: str, params: dict, data: dict, _):
        result_type, content = await self.fetch_content(result)
        modified_content = await self.process_request_callback(result_type, content)
        if modified_content is None:
            modified_content = content
        yield result_type, modified_content

    async def _make_request_cleanup(self, api_key):
        if api_key:
            assert isinstance(self.semaphores, dict)
            self.semaphores[api_key].release()
            self.api_keys_queue.put_nowait(api_key)
