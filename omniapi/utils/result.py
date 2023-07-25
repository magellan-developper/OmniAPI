import logging
from enum import auto, Enum
from typing import Optional

from omniapi.utils.config import APIConfig
from omniapi.utils.download import download_file_to_path
from omniapi.utils.exception import raise_exception
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

    async def download(self, url: Optional[str] = None,
                       method: str = 'GET',
                       data: Optional[dict] = None,
                       settings: Optional[dict] = None):
        if url is None:
            result = await download_file_to_path(
                self.response,
                self.config.files_download_directory,
                self.config.file_name_mode,
                self.logger
            )
            return ResultType.FILE, result
        if method == 'GET':
            return Result.get(url, data, settings)
        elif method == 'POST':
            return Result.post(url, data, settings)
        raise_exception(f"Method {method} is not supported!", self.config.error_strategy, logger=self.logger)

    @staticmethod
    def get(url: str, params: Optional[dict] = None, settings: Optional[dict] = None):
        return ResultType.REQUEST, ("GET", url, params, settings)

    @staticmethod
    def post(url: str, data: Optional[dict] = None, settings: Optional[dict] = None):
        return ResultType.REQUEST, ("POST", url, data, settings)

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
            return method, endpoint, payload_method(start_from + per_page)
