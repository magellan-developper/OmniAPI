import logging
from abc import ABC
from typing import Optional

from omniapi.clients.base import BaseClient
from omniapi.utils.response import Response, ResponseType


class APIClient(BaseClient, ABC):
    """
    A base class for API Clients. This class is designed to be extended by
    other classes that make API requests. The class includes methods for
    setting up requests, cleaning up requests, and processing responses.

    Attributes:
        logger (logging.Logger): Logger for this class.

    """

    logger = logging.Logger(__name__)

    def __init__(self, *args, **kwargs):
        """Initialize a new instance of APIClient."""

        super().__init__(*args, **kwargs)

    async def make_request_setup(self, url: str):
        """
        Set up for making an API request. Handles rate limiting and acquiring API keys.

        Args:
            url (str): The url of the request.

        Returns:
            Optional[str]: The API key for the request, if applicable.

        """
        state = self.get_state(url)

        if state.api_keys_queue is None:
            await self._sleep_for_rate_limit(state)
        else:
            api_key = state.api_keys_queue.get()
            await self._sleep_for_rate_limit(state, api_key)
            await state.semaphores[api_key].acquire()
            state.api_keys_queue.put_nowait(api_key)
            return api_key

    @staticmethod
    async def get_result_content(result: Response):
        """
        Gets the content of the result based on the content type in the response header.

        Args:
            result (Response): The result object.

        Returns:
            Tuple[ResponseType, Any]: The result type and content.

        """
        file_type = result.response.headers['Content-Type'].split(';')[0]
        if file_type == 'text/plain':
            response_type, content = await result.text()
        elif file_type == 'application/json':
            response_type, content = await result.json()
        else:
            response_type, content = await result.download()
        return response_type, content

    async def request_callback(self, response: Response, setup_info):
        response_type, content = await self.get_result_content(response)
        async for item in self.process_request(response_type, content):
            yield item

    async def process_request(self, response_type: ResponseType, content):
        yield

    async def make_request_cleanup(self, url: str, api_key: Optional[str] = None):
        """
        Clean up after making an API request. Handles releasing semaphores and returning API keys.

        Args:
            url (str): The url of the request.
            api_key (Optional[str], optional): The API key used in the request. Defaults to None.

        """
        if api_key is not None:
            state = self.get_state(url)
            state.semaphores[api_key].release()
            state.api_keys_queue.put_nowait(api_key)
