import asyncio
import datetime
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from ssl import SSLContext
from typing import Optional, Union, Sequence, Any
from urllib.parse import urljoin

import aiofiles
import aiohttp
import aiohttp_retry
from aiohttp import BasicAuth, BaseConnector
from aiohttp.abc import AbstractCookieJar
from aiohttp_retry import RetryClient
from tqdm.asyncio import tqdm_asyncio

from omniapi.utils.config import APIConfig, SessionConfig
from omniapi.utils.download import FileNameMode
from omniapi.utils.helper import numeric, get_wait_time
from omniapi.utils.types import PathType


@dataclass
class ClientState:
    client: aiohttp_retry.RetryClient
    api_keys_queue: Optional[asyncio.Queue]
    semaphores: dict
    last_request_time: dict
    wait_time: float


class BaseClient(ABC):
    """Base Class for API Clients"""
    logger = logging.getLogger(__name__)
    static_counter = -1

    def __init__(self,
                 base_url: str,
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

        self.base_url = base_url

        if files_download_directory is not None:
            files_download_directory = Path(files_download_directory)
            files_download_directory.mkdir(exist_ok=True, parents=True)

        api_config = APIConfig(
            base_url=base_url,
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
        self.endpoint_configs: dict[str, APIConfig] = dict()
        self.client_state: dict[str, ClientState] = dict()

        self.client_state[self.base_url] = self.initialize_client(api_config, session_config)
        self.endpoint_configs[self.base_url] = api_config

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
        return self.client_state[endpoint].client

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

        if not self.client_state:
            if session_config is None:
                session_config = SessionConfig()
            client = RetryClient(
                retry_options=api_config.retry_options,
                logger=self.logger,
                **session_config.to_dict(),
            )
        elif session_config is not None:
            client = RetryClient(
                retry_options=api_config.retry_options,
                logger=self.logger,
                **session_config.to_dict(),
            )
        else:
            client = self.client_state[api_config.base_url].client

        return ClientState(
            client=client,
            api_keys_queue=api_keys_queue,
            semaphores=semaphores,
            last_request_time=last_request_time,
            wait_time=wait_time,
        )

    def add_settings(self, base_url: str, *, max_requests_per_interval=None,
                     interval_unit=None, max_concurrent_requests=None, api_keys=None, allow_redirects=None,
                     max_redirects=None, timeout=None, files_download_directory=None,
                     file_name_mode=None, error_strategy=None, display_progress_bar=None,
                     auth=None, connector=None, cookie_jar=None, cookies=None, headers=None, ssl=None,
                     trust_env=None, proxy=None, proxy_auth=None, proxies=None,
                     api_config: Optional[APIConfig] = None, session_config: Optional[SessionConfig] = None):
        if base_url in self.endpoint_configs:
            raise RuntimeError(f"Base URL {base_url} has already been configured!")

        # API Config Settings
        if api_config is None:
            api_config = APIConfig(base_url=base_url)
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
            self.client_state[base_url] = self.initialize_client(api_config)
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
        self.client_state[base_url] = self.initialize_client(api_config)

    async def _sleep_for_rate_limit(self, base_url, api_key=None):
        client_state = self.client_state[base_url]
        semaphore = client_state.semaphores[api_key]
        async with semaphore:
            last_request_time = client_state.last_request_time[api_key]
            elapsed = time.monotonic() - last_request_time
            if client_state.wait_time > 0 and (sleep_time := max(client_state.wait_time - elapsed, 0)) > 0:
                await asyncio.sleep(sleep_time)
            client_state.last_request_time[api_key] = time.monotonic()

    @staticmethod
    def get_hash(method: str, endpoint: str, hash_items):
        return hash(hash(method) + hash(endpoint) + hash(hash_items))

    @abstractmethod
    async def request_callback(self, result: Result, endpoint: str, params: dict, data: dict, setup_info):
        ...

    async def _make_request_setup(self) -> Any:
        pass

    async def _make_request_cleanup(self, setup_info):
        pass

    def setup_request(self, endpoint, headers, params, data, setup_info):
        pass

    async def _make_request(self, method: str, endpoint: str, params: dict = None, data: dict = None):
        new_requests = []
        url = self._create_url(endpoint)

        headers = {}
        params = {} if params is None else params
        data = {} if data is None else data

        setup_info = await self._make_request_setup()
        hash_items = self.setup_request(endpoint, headers, params, data, setup_info)
        if (request_hash := self.get_hash(method, endpoint, hash_items)) not in self.visited:
            self.visited.add(request_hash)
        else:
            return
        try:
            async with self.client.request(method, url, headers=headers, params=params, json=data,
                                           timeout=self.timeout) as response:
                response.raise_for_status()
                response_result = Result(response, self.config)
                # noinspection PyTypeChecker
                async for temp in self.request_callback(response_result, endpoint, params, data, setup_info):
                    if temp is None:
                        continue
                    result_type, result = temp
                    match result_type:
                        case ResultType.JSON:
                            self.stats.json += 1
                            if self.config.export_results_path is not None:
                                self.results['json'].append(result)
                        case ResultType.TEXT:
                            self.stats.text += 1
                            if self.config.export_results_path is not None:
                                self.results['text'].append(result)
                        case ResultType.FILE:
                            self.stats.text += 1
                            if self.config.export_results_path is not None:
                                self.results['files'].append(result)
                        case ResultType.REQUEST:
                            self.stats.new_requests += 1
                            new_requests.append(result)
                        case _:
                            self.stats.wrong_types += 1
                            raise RuntimeWarning(f"Result {result} cannot be processed!")

        except aiohttp.ClientResponseError as e:
            self.logger.error("request_failed", method=method, url=url, data=data, error=str(e))
            self.stats.failed_requests += 1
        except aiohttp.ClientConnectorError as e:
            self.logger.error("failed_connection", method=method, url=url, data=data, error=str(e))
            self.stats.failed_connections += 1
        finally:
            await self._make_request_cleanup(setup_info)
            self.stats.total += 1
            for new_method, new_endpoint, new_data in new_requests:
                self.tasks += [asyncio.create_task(method(endpoint, data)) for method, endpoint, data in
                               self.package_requests(new_method, new_endpoint, new_data)]

    async def get(self, endpoint: str, params: dict = None) -> Any:
        await self._make_request("GET", endpoint, params=params)

    async def post(self, endpoint: str, data: dict = None) -> Any:
        await self._make_request("POST", endpoint, data=data)

    @staticmethod
    async def write_json(filename, data):
        async with aiofiles.open(filename, mode='w') as f:
            await f.write(json.dumps(data))

    async def export_results(self, results):
        export_path = self.config.export_results_path
        if export_path is None:
            return
        export_path = Path(self.config.export_results_path)
        if export_path.exists():
            self.logger.error(f"File {export_path} already exists! Overwriting file...")

        export_path.parent.mkdir(exist_ok=True, parents=True)
        await self.write_json(self.config.export_results_path, results)

    def get_request_handler(self, method):
        method = method.upper()
        if method == 'GET':
            return self.get
        elif method == 'POST':
            return self.post
        else:
            raise ValueError("Method must be either GET or POST!")

    def package_requests(self, methods: Union[str, Sequence[str]],
                         endpoints: Union[str, Sequence[str]],
                         data_list: Optional[Union[Sequence[dict], dict]]):
        if isinstance(methods, str):
            methods = [self.get_request_handler(methods)]
        else:
            methods = list(map(self.get_request_handler, methods))
        endpoints = [endpoints] if isinstance(endpoints, str) else endpoints
        data_list = [data_list] if isinstance(data_list, dict) or data_list is None else data_list
        max_length = max(len(methods), len(endpoints), len(data_list))
        assert {len(methods), len(endpoints), len(data_list)}.issubset({1, max_length})

        if len(methods) != max_length:
            methods *= max_length
        if len(endpoints) != max_length:
            endpoints *= max_length
        if len(data_list) != max_length:
            data_list *= max_length
        for method, endpoint, data in zip(methods, endpoints, data_list):
            yield method, endpoint, data

    async def schedule_requests(self, methods: Union[str, list[str]],
                                endpoints: Union[str, list[str]],
                                data_list: Optional[Union[list[dict], dict]]):
        tasks = [asyncio.create_task(method(endpoint, data)) for method, endpoint, data in
                 self.package_requests(methods, endpoints, data_list)]
        self.static_counter += 1

        while tasks:
            if self.display_progress_bar:
                await tqdm_asyncio.gather(*tasks, position=self.static_counter)
            else:
                await asyncio.gather(*tasks)
            tasks, self.tasks = self.tasks, []

    async def run(self, methods: Union[str, list[str]],
                  endpoints: Union[str, list[str]],
                  data_list: Optional[Union[tuple[dict], list[dict], dict]]):
        await self.schedule_requests(methods, endpoints, data_list)
        await self.export_results(self.results)
        return self.results