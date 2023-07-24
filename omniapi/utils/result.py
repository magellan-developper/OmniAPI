import logging
from typing import Optional, Union

from omniapi.utils.config import APIConfig
from omniapi.utils.download import download_file_to_path
from omniapi.utils.exception import raise_exception
from omniapi.utils.state import ClientState


class Result:
    def __init__(self, response, config: APIConfig, state: ClientState, logger: logging.Logger):
        self.response = response
        self.config = config
        self.state = state
        self.logger = logger

    async def json(self) -> dict:
        return await self.response.json()

    async def text(self) -> str:
        return await self.response.text()

    async def url(self):
        return self.response.url.path

    async def download(self, url: Optional[str] = None,
                       method: str = 'GET',
                       data: Optional[dict] = None) -> Union[dict, tuple]:
        if url is None:
            return await download_file_to_path(
                self.response,
                self.config.files_download_directory,
                self.config.file_name_mode,
                self.logger
            )
        if method == 'GET':
            return Result.get(url, data)
        elif method == 'POST':
            return Result.post(url, data)
        raise_exception(f"Method {method} is not supported!", self.config.error_strategy, logger=self.logger)

    @staticmethod
    def get(url: str, params: Optional[dict] = None):
        return "GET", url, params

    @staticmethod
    def post(url: str, data: Optional[dict] = None):
        return "POST", url, data

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
