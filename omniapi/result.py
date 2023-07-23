import hashlib
import hashlib
import mimetypes
import os
import typing
from enum import Enum, auto
from pathlib import Path
from typing import Optional
from urllib.parse import unquote_to_bytes

import aiofiles
import aiohttp


class ResultType(Enum):
    JSON = auto()
    TEXT = auto()
    REQUEST = auto()
    FILE = auto()


class Result:
    def __init__(self, response, config):
        self.response = response
        self.config = config

    async def json(self):
        result = await self.response.json()
        return ResultType.JSON, result

    async def text(self):
        result = await self.response.text()
        return ResultType.TEXT, result

    async def download(self):
        url = self.response.url.path
        if self.config.files_download_directory is None:
            return ResultType.FILE, url
        result = await self._download_file_to_path(self.response)
        return ResultType.FILE, result

    async def download_url_file(self, url: str):
        if self.config.files_download_directory is None:
            return ResultType.FILE, url
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=self.config.timeout) as response:
                if response.status == 200:
                    result = await self._download_file_to_path(response)
                else:
                    return None
        return ResultType.FILE, result

    @staticmethod
    def get(endpoint: str, data: Optional[dict] = None):
        return ResultType.REQUEST, ("GET", endpoint, data)

    @staticmethod
    def post(endpoint: str, data: Optional[dict] = None):
        return ResultType.REQUEST, ("POST", endpoint, data)

    def paginate(self, endpoint: str, content: dict, start_path: str, per_page_path: str,
                 total_path: str, payload_method, sep: str = '.'):
        method = self.response.request_info.method
        start, per_page, total = content, content, content
        for key in start_path.split(sep):
            start = start[key]
        for key in per_page_path.split(sep):
            per_page = per_page[key]
        for key in total_path.split(sep):
            total = total[key]

        start_from, per_page, total = int(start), int(per_page), int(total)
        if start_from + per_page < total:
            return ResultType.REQUEST, (method, endpoint, payload_method(start_from + per_page))
