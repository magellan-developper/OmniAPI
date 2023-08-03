import logging
from enum import auto, Enum
from pathlib import Path
from typing import Optional, Union, Callable
from aiohttp import ClientResponse

from omniapi.utils.config import APIConfig
from omniapi.utils.download import download_file_to_path
from omniapi.utils.state import ClientState


class ResponseType(Enum):
    """
    Enum representing the type of the result that can be returned by a request.
    """
    TEXT = auto()
    JSON = auto()
    FILE = auto()
    REQUEST = auto()


class Response:
    """
    Class that encapsulates a response returned from a request.

    Attributes:
        response: The aiohttp response object.
        config (APIConfig): The configuration object of the API.
        state (ClientState): The state object for the client.
        logger (logging.Logger): Logger instance for recording events related to the Result.

    """

    def __init__(self, response: ClientResponse, config: APIConfig, state: ClientState, logger: logging.Logger):
        self.response = response
        self.config = config
        self.state = state
        self.logger = logger

    def get_url(self):
        return str(self.response.url)

    async def json(self):
        """
        Parses the response as a JSON.

        Returns:
            (ResponseType.JSON, dict): A tuple of ResultType.JSON and the parsed JSON content.

        """
        result = await self.response.json()
        return ResponseType.JSON, result

    async def text(self):
        """
        Parses the response as a text.

        Returns:
            (ResponseType.TEXT, str): A tuple of ResultType.TEXT and the parsed text content.

        """
        result = await self.response.json()
        return ResponseType.TEXT, result

    async def download(self, dir_path: Optional[Union[Path, str]] = None):
        """
        Downloads the content of the response to a specified directory.

        Args:
            dir_path (Union[Path, str], optional): The directory path where the file should be downloaded.

        Returns:
            (ResponseType.FILE, dict): A tuple of ResultType.FILE and a dictionary with the file details.

        """
        result = await download_file_to_path(
            self.response,
            self.config,
            dir_path,
            self.logger
        )
        return ResponseType.FILE, result

    @staticmethod
    def get(url: str, params: Optional[dict] = None, settings: Optional[dict] = None):
        """
        Constructs a GET request.

        Args:
            url (str): The URL for the GET request.
            params (dict, optional): The parameters for the GET request.
            settings (dict, optional): Additional settings for the request.

        Returns:
            (ResponseType.REQUEST, tuple): A tuple of ResultType.REQUEST and a tuple with the request details.

        """
        return ResponseType.REQUEST, ("GET", url, params, settings)

    @staticmethod
    def post(url: str, data: Optional[dict] = None, settings: Optional[dict] = None):
        """
        Constructs a POST request.

        Args:
            url (str): The URL for the POST request.
            data (dict, optional): The data to be sent in the POST request.
            settings (dict, optional): Additional settings for the request.

        Returns:
            (ResponseType.REQUEST, tuple): A tuple of ResultType.REQUEST and a tuple with the request details.

        """
        return ResponseType.REQUEST, ("POST", url, data, settings)

    def paginate(self, url: str, content: dict, start_path: str, per_page_path: str,
                 total_path: str, payload_method: Callable[[int], dict], sep: str = '.'):
        """
        Generates the next pagination request.

        Args:
            url (str): The URL for the pagination request.
            content (dict): The content of the previous response.
            start_path (str): The path in the content where the start page number can be found.
            per_page_path (str): The path in the content where the number of items per page can be found.
            total_path (str): The path in the content where the total number of items can be found.
            payload_method (Callable[[int], dict]): A function that constructs the payload for the request given a page number.
            sep (str): The separator for the paths.

        Returns:
            tuple: A tuple with the method, url, and payload for the next request if there are more pages, None otherwise.
        """
        method = self.response.request_info.method
        start = self._get_paginate_elem(start_path, content, sep)
        per_page = self._get_paginate_elem(per_page_path, content, sep)
        total = self._get_paginate_elem(total_path, content, sep)

        if start + per_page < total:
            return ResultType.REQUEST, (method, url, payload_method(start + per_page))

    @staticmethod
    def _get_paginate_elem(path: str, content: dict, sep: str):
        """
        Fetches a pagination element from the content.

        Args:
            path (str): The path to the pagination element in the content.
            content (dict): The content of the response.
            sep (str): The separator for the path.

        Returns:
            int: The pagination element.
        """
        for key in path.split(sep):
            content = content[key]
        return int(content)
