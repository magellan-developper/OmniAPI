import asyncio
import datetime
import logging
import time
from abc import ABC, abstractmethod
from itertools import cycle
from pathlib import Path
from ssl import SSLContext
from typing import Optional, Union, Sequence, Any, Dict, Callable, Coroutine
from urllib.parse import urlparse, urlunparse

import aiohttp
from aiohttp import BasicAuth, BaseConnector
from aiohttp.abc import AbstractCookieJar
from aiohttp_retry import RetryClient
from tqdm import tqdm

from omniapi.utils.config import APIConfig, SessionConfig
from omniapi.utils.download import FileNameMode
from omniapi.utils.exception import raise_exception
from omniapi.utils.helper import numeric, get_wait_time
from omniapi.utils.result import Result
from omniapi.utils.state import ClientState
from omniapi.utils.types import PathType, OptionalDictSequence, StringSequence


class BaseClient(ABC):
    """Base Class for API Clients"""
    logger = logging.getLogger(__name__)
    clients = []

    def __init__(self,
                 max_requests_per_interval: Union[Sequence[numeric], numeric] = 5,
                 interval_unit: Union[Sequence[datetime.timedelta], datetime.timedelta] = datetime.timedelta(seconds=1),
                 max_concurrent_requests: int = 1,
                 api_keys: Optional[Sequence[str]] = None,
                 allow_redirects=True,
                 max_redirects: int = 0,
                 timeout: float = 10.0,
                 files_download_directory: PathType = None,
                 file_name_mode: FileNameMode = FileNameMode.URL_HASH_MD5,
                 error_strategy: str = 'log',
                 display_progress_bar: bool = False, *,
                 auth: Optional[BasicAuth] = None,
                 connector: Optional[BaseConnector] = None,
                 cookie_jar: Optional[AbstractCookieJar] = None,
                 cookies: Optional[dict] = None,
                 headers: Optional[dict] = None,
                 ssl: Optional[Union[bool, SSLContext]] = None,
                 trust_env: bool = False,
                 proxy: Optional[str] = None,
                 proxy_auth: Optional[BasicAuth] = None,
                 proxies: Optional[Sequence[str]] = None,
                 ):

        if files_download_directory is not None:
            files_download_directory = Path(files_download_directory)
            files_download_directory.mkdir(exist_ok=True, parents=True)

        api_config = APIConfig(
            max_requests_per_interval=max_requests_per_interval,
            interval_unit=interval_unit,
            max_concurrent_requests=max_concurrent_requests,
            api_keys=api_keys,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            timeout=timeout,
            error_strategy=error_strategy,
            files_download_directory=files_download_directory,
            file_name_mode=file_name_mode,
        )

        session_config = SessionConfig(
            auth=auth,
            connector=connector,
            cookie_jar=cookie_jar,
            cookies=cookies,
            headers=headers,
            ssl=ssl,
            trust_env=trust_env,
            proxy=proxy,
            proxy_auth=proxy_auth,
            proxies=proxies,
        )

        # None represents global config / endpoint
        self.endpoint_configs: Dict[Optional[str], APIConfig] = dict()
        self.endpoint_states: Dict[Optional[str], ClientState] = dict()

        self.endpoint_states[None] = self.initialize_client(api_config, session_config)
        self.endpoint_configs[None] = api_config

        self.display_progress_bar = display_progress_bar

        self.visited = set()
        self.tasks = []
        # use trace config to collect stats

    @classmethod
    def from_config(cls, api_config: APIConfig,
                    session_config: SessionConfig = SessionConfig()):
        return BaseClient(
            **api_config.to_dict(),
            **session_config.to_dict()
        )

    def get_client(self, endpoint: Optional[str] = None):
        return self.endpoint_states[endpoint].client

    def initialize_client(self, api_config: APIConfig,
                          session_config: Optional[SessionConfig] = None):
        num_api_keys = 0 if api_config.api_keys is None else len(api_config.api_keys)
        api_keys_queue = asyncio.Queue() if num_api_keys > 0 else None

        # Setup Semaphores and Request Time to throttle request rate
        semaphores = {}
        last_request_time = {}

        if api_keys_queue is not None:
            assert api_config.api_keys is not None
            for api_key in api_config.api_keys:
                api_keys_queue.put_nowait(api_key)
                last_request_time[api_key] = 0.0
                semaphores[api_key] = asyncio.Semaphore(api_config.max_concurrent_requests)
        else:
            last_request_time[None] = 0
            semaphores[None] = asyncio.Semaphore(api_config.max_concurrent_requests)

        wait_time = get_wait_time(api_config, self.logger)

        if not self.endpoint_states:
            if session_config is None:
                session_config = SessionConfig()
            client = RetryClient(
                retry_options=api_config.retry_options,
                logger=self.logger,
                **session_config.to_dict(),
            )
            self.clients.append(client)
        elif session_config is not None:
            client = RetryClient(
                retry_options=api_config.retry_options,
                logger=self.logger,
                **session_config.to_dict(),
            )
            self.clients.append(client)
        else:
            client = self.endpoint_states[api_config.base_url].client

        return ClientState(
            client=client,
            api_keys_queue=api_keys_queue,
            semaphores=semaphores,
            last_request_time=last_request_time,
            wait_time=wait_time,
        )

    def add_settings(self, url: str, *, max_requests_per_interval=None,
                     interval_unit=None, max_concurrent_requests=None, api_keys=None, allow_redirects=None,
                     max_redirects=None, timeout=None, files_download_directory=None,
                     file_name_mode=None, error_strategy=None, display_progress_bar=None,
                     auth=None, connector=None, cookie_jar=None, cookies=None, headers=None, ssl=None,
                     trust_env=None, proxy=None, proxy_auth=None, proxies=None,
                     api_config: Optional[APIConfig] = None, session_config: Optional[SessionConfig] = None):
        base_url = urlparse(url).netloc
        if base_url in self.endpoint_configs:
            raise_exception(f"Base URL {base_url} has already been configured, overwriting settings...",
                            exception_type='warning', logger=self.logger)

        # API Config Settings
        if api_config is None:
            api_config = APIConfig()
        if max_requests_per_interval is not None:
            api_config.max_requests_per_interval = max_requests_per_interval
        if interval_unit is not None:
            api_config.interval_unit = interval_unit
        if max_concurrent_requests is not None:
            api_config.max_concurrent_requests = max_concurrent_requests
        if api_keys is not None:
            api_config.api_keys = api_keys
        if allow_redirects is not None:
            api_config.allow_redirects = allow_redirects
        if max_redirects is not None:
            api_config.max_redirects = max_redirects
        if timeout is not None:
            api_config.timeout = timeout
        if files_download_directory is not None:
            api_config.files_download_directory = files_download_directory
        if file_name_mode is not None:
            api_config.file_name_mode = file_name_mode
        if error_strategy is not None:
            api_config.error_strategy = error_strategy
        if display_progress_bar is not None:
            api_config.display_progress_bar = display_progress_bar

        self.endpoint_configs[base_url] = api_config

        # Session Config Settings
        if all(x is None for x in [auth, connector, cookie_jar, cookies, headers,
                                   ssl, trust_env, proxy, proxy_auth, proxies]) and session_config is None:
            self.endpoint_states[base_url] = self.initialize_client(api_config)
            return
        if session_config is None:
            session_config = SessionConfig()
        if auth is not None:
            session_config.auth = auth
        if connector is not None:
            session_config.connector = connector
        if cookie_jar is not None:
            session_config.cookie_jar = cookie_jar
        if cookies is not None:
            session_config.cookies = cookies
        if headers is not None:
            session_config.headers = headers
        if ssl is not None:
            session_config.ssl = ssl
        if trust_env is not None:
            session_config.trust_env = trust_env
        if proxy is not None:
            session_config.proxy = proxy
        if proxy_auth is not None:
            session_config.proxy_auth = proxy_auth
        if proxies is not None:
            session_config.proxies = proxies
        self.endpoint_states[base_url] = self.initialize_client(api_config)

    @staticmethod
    async def sleep_for_rate_limit(state: ClientState, api_key=None):
        semaphore = state.semaphores[api_key]
        async with semaphore:
            last_request_time = state.last_request_time[api_key]
            elapsed = time.monotonic() - last_request_time
            if state.wait_time > 0 and (sleep_time := max(state.wait_time - elapsed, 0)) > 0:
                await asyncio.sleep(sleep_time)
            state.last_request_time[api_key] = time.monotonic()

    @staticmethod
    def get_hash(method: str, url: str, hash_items):
        return hash(hash(method) + hash(url) + hash(hash_items))

    @abstractmethod
    async def request_callback(self, result: Result, url: str, data: dict, setup_info):
        ...

    async def _make_request_setup(self, base_url) -> Any:
        pass

    async def _make_request_cleanup(self, setup_info):
        pass

    def setup_request(self, url: str, headers: dict, data: dict, setup_info: Any):
        pass

    def get_state(self, url: str):
        if (base_url := urlparse(url).netloc) in self.endpoint_states:
            return self.endpoint_states[base_url]
        else:
            return self.endpoint_states[None]

    def get_config(self, url: str):
        if (base_url := urlparse(url).netloc) in self.endpoint_configs:
            return self.endpoint_configs[base_url]
        else:
            return self.endpoint_configs[None]

    async def _make_request(self, method: str, url: str, data: dict = None):
        new_requests = []

        # Setup headers
        headers = {}
        data = data or {}

        setup_info = await self._make_request_setup(url)
        # noinspection PyNoneFunctionAssignment
        hash_items = self.setup_request(url, headers, data, setup_info)
        request_hash = self.get_hash(method, url, hash_items)
        if request_hash in self.visited:
            return
        self.visited.add(request_hash)
        request_params = {'params': data, 'json': {}} if method == "GET" else {'params': {}, 'json': data}

        state = self.get_state(url)
        config = self.get_config(url)

        parsed_url = urlparse(url)
        try:
            async with state.client.request(
                    method, url, headers=headers, **request_params, timeout=config.timeout) as response:
                response_result = Result(response, config, state, self.logger)
                # noinspection PyTypeChecker
                async for result in self.request_callback(response_result, url, data, setup_info):
                    new_method, new_url, new_data = result
                    new_parsed_url = urlparse(new_url)
                    if new_parsed_url.netloc == '':
                        # noinspection PyProtectedMember
                        new_url = urlunparse(new_parsed_url._replace(scheme=parsed_url.scheme, netloc=parsed_url.netloc))
                    new_requests.append((new_method, new_url, new_data))
        except aiohttp.ClientResponseError as e:
            self.logger.error(
                {"message": "request_failed", "method": method, "url": url, "data": data, "error": str(e)})
        except aiohttp.ClientConnectorError as e:
            self.logger.error(
                {"message": "failed_connection", "method": method, "url": url, "data": data, "error": str(e)})
        finally:
            await self._make_request_cleanup(setup_info)
            for new_method, new_url, new_data in new_requests:
                self.tasks += [asyncio.create_task(self.get_request_handler(method)(url, data)) for method, url, data in
                               self.package_requests(new_method, new_url, new_data)]

    async def get(self, url: str, params: dict = None):
        await self._make_request("GET", url, data=params)

    async def post(self, url: str, data: dict = None):
        await self._make_request("POST", url, data=data)

    def get_request_handler(self, method) -> Callable[[str, dict], Coroutine]:
        method = method.upper()
        if method == 'GET':
            return self.get
        elif method == 'POST':
            return self.post
        else:
            raise ValueError("Method must be either GET or POST!")

    @staticmethod
    def package_requests(methods: StringSequence, endpoints: StringSequence,
                         data_list: OptionalDictSequence):
        methods = [methods] if isinstance(methods, str) else methods
        endpoints = [endpoints] if isinstance(endpoints, str) else endpoints
        data_list = [data_list] if isinstance(data_list, dict) or data_list is None else data_list
        max_length = max(len(methods), len(endpoints), len(data_list))
        assert {len(methods), len(endpoints), len(data_list)}.issubset({1, max_length})

        for _ in range(max_length):
            yield next(cycle(methods)), next(cycle(endpoints)), next(cycle(data_list))

    async def schedule_requests(self, methods: StringSequence, endpoints: StringSequence,
                                data_list: OptionalDictSequence):
        tasks = [asyncio.create_task(self.get_request_handler(method)(endpoint, data))
                 for method, endpoint, data in self.package_requests(methods, endpoints, data_list)]

        if self.display_progress_bar:
            pbar = tqdm()
            while tasks:
                for task in asyncio.as_completed(tasks):
                    await task
                    pbar.update(1)
                tasks, self.tasks = self.tasks, []

            pbar.close()
        else:
            while tasks:
                await asyncio.gather(*tasks)
                tasks, self.tasks = self.tasks, []

    async def run(self, methods: StringSequence, endpoints: StringSequence, data_list: OptionalDictSequence):
        await self.schedule_requests(methods, endpoints, data_list)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        for client in self.clients:
            client.close()
