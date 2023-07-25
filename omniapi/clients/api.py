import logging
from abc import ABC
from typing import Optional

from omniapi.clients.base import BaseClient
from omniapi.utils.result import Result


class APIClient(BaseClient, ABC):
    """Base class for API Clients"""

    logger = logging.Logger(__name__)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def make_request_setup(self, url: str):
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
    async def get_result_content(result: Result):
        file_type = result.response.headers['Content-Type'].split(';')[0]
        if file_type == 'text/plain':
            result_type, content = await result.text()
        elif file_type == 'application/json':
            result_type, content = await result.json()
        else:
            result_type, content = await result.download()
        return result_type, content

    async def make_request_cleanup(self, url: str, api_key: Optional[str] = None):
        if api_key is not None:
            state = self.get_state(url)
            state.semaphores[api_key].release()
            state.api_keys_queue.put_nowait(api_key)
