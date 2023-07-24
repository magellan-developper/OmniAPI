from omniapi.clients.base import BaseClient


class APIClient(BaseClient):
    def __init__(self, base_url: str, *args, **kwargs):
        super().__init__(base_url, *args, **kwargs)

    async def _make_request_setup(self, url: str):
        state = self.get_state(url)

        if state.api_keys_queue is None:
            await self.sleep_for_rate_limit(state)
        else:
            api_key = state.api_keys_queue.get()
            await self.sleep_for_rate_limit(state, api_key)
            await state.semaphores[api_key].acquire()
            state.api_keys_queue.put_nowait(api_key)
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
        yield modified_content

    async def _make_request_cleanup(self, api_key):
        if api_key:
            assert isinstance(self.semaphores, dict)
            self.semaphores[api_key].release()
            self.api_keys_queue.put_nowait(api_key)