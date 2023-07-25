import logging
from enum import auto, Enum
from pathlib import Path
from typing import Optional, Union, Callable

from omniapi.utils.config import APIConfig
from omniapi.utils.download import download_file_to_path
from omniapi.utils.state import ClientState


class ResultType(Enum):
    TEXT = auto()
    JSON = auto()
    FILE = auto()
    REQUEST = auto()


class Result:
    def __init__(self, response, config: APIConfig, state: ClientState, logger: logging.Logger):
        self.response = response
        self.config = config
        self.state = state
        self.logger = logger

    async def json(self):
        result = await self.response.json()
        return ResultType.JSON, result

    async def text(self):
        result = await self.response.json()
        return ResultType.TEXT, result

    async def url(self):
        result = await self.response.json()
        return ResultType.TEXT, result

    async def download(self, dir_path: Optional[Union[Path, str]] = None):
        result = await download_file_to_path(
            self.response,
            self.config,
            dir_path,
            self.logger
        )
        return ResultType.FILE, result

    @staticmethod
    def get(url: str, params: Optional[dict] = None, settings: Optional[dict] = None):
        return ResultType.REQUEST, ("GET", url, params, settings)

    @staticmethod
    def post(url: str, data: Optional[dict] = None, settings: Optional[dict] = None):
        return ResultType.REQUEST, ("POST", url, data, settings)

    def paginate(self, url: str, content: dict, start_path: str, per_page_path: str,
                 total_path: str, payload_method: Callable[[int], dict], sep: str = '.'):
        method = self.response.request_info.method
        start = self._get_paginate_elem(start_path, content, sep)
        per_page = self._get_paginate_elem(per_page_path, content, sep)
        total = self._get_paginate_elem(total_path, content, sep)

        if start + per_page < total:
            return method, url, payload_method(start + per_page)

    @staticmethod
    def _get_paginate_elem(path: str, content: dict, sep: str):
        for key in path.split(sep):
            content = content[key]
        return int(content)
