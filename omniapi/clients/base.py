import asyncio
import datetime
import logging
import time
from abc import ABC, abstractmethod
from itertools import cycle
from pathlib import Path
from typing import Optional, Union, Sequence, Any, Dict, Callable, Coroutine
from urllib.parse import urlparse, urlunparse

import aiohttp
from aiohttp import BasicAuth, BaseConnector
from aiohttp.abc import AbstractCookieJar
from aiohttp_retry import RetryClient
from tqdm import tqdm

from omniapi.utils.config import APIConfig, SessionConfig
from omniapi.utils.download import FileNameStrategy
from omniapi.utils.exception import raise_exception
from omniapi.utils.helper import get_wait_time
from omniapi.utils.response import Response, ResponseType
from omniapi.utils.state import ClientState
from omniapi.utils.stats import ClientStats
from omniapi.utils.types import PathType, OptionalDictSequence, StringSequence
from omniapi.utils.types import numeric


class BaseClient(ABC):
    """
    Abstract Base Class for Request Clients.

    Args:
        max_requests_per_interval (Union[Sequence[numeric], numeric], optional): Maximum number of requests per interval.
            Defaults to 5.
        interval_unit (Union[Sequence[datetime.timedelta], datetime.timedelta], optional): Time interval for requests.
            Defaults to datetime.timedelta(seconds=1).
        max_concurrent_requests (int, optional): Maximum number of concurrent requests. Defaults to 1.
        api_keys (Optional[Sequence[str]], optional): Sequence of API keys to be used. Defaults to None.
        allow_redirects (bool, optional): Whether redirects should be allowed. Defaults to True.
        max_redirects (int, optional): Maximum number of redirects allowed. Defaults to 0.
        timeout (float, optional): Request timeout in seconds. Defaults to 10.0.
        files_download_directory (PathType, optional): Path to the directory where files should be downloaded. Defaults to None.
        file_name_mode (FileNameStrategy, optional): Strategy for naming files. Defaults to FileNameStrategy.URL_HASH_MD5.
        error_strategy (str, optional): Strategy for error handling. Defaults to 'log'.
        display_progress_bar (bool, optional): Whether to display a progress bar. Defaults to False.
        auth (Optional[BasicAuth], optional): Basic auth credentials. Defaults to None.
        connector (Optional[BaseConnector], optional): Connector to use. Defaults to None.
        cookie_jar (Optional[AbstractCookieJar], optional): Cookie jar to use. Defaults to None.
        cookies (Optional[dict], optional): Cookies to use. Defaults to None.
        headers (Optional[dict], optional): Headers to use. Defaults to None.
        trust_env (bool, optional): Whether to trust environment variables for things like proxies. Defaults to False.
    """

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    clients = []
    stats = ClientStats()

    def __init__(self,
                 max_requests_per_interval: Union[Sequence[numeric], numeric] = 5,
                 interval_unit: Union[Sequence[datetime.timedelta], datetime.timedelta] = datetime.timedelta(seconds=1),
                 max_concurrent_requests: int = 1,
                 api_keys: Optional[Sequence[str]] = None,
                 allow_redirects=True,
                 max_redirects: int = 0,
                 timeout: float = 10.0,
                 files_download_directory: PathType = None,
                 file_name_mode: FileNameStrategy = FileNameStrategy.URL_HASH_MD5,
                 error_strategy: str = 'log',
                 display_progress_bar: bool = False, *,
                 auth: Optional[BasicAuth] = None,
                 connector: Optional[BaseConnector] = None,
                 cookie_jar: Optional[AbstractCookieJar] = None,
                 cookies: Optional[dict] = None,
                 headers: Optional[dict] = None,
                 trust_env: bool = False):
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
            trust_env=trust_env,
        )

        # None represents global config / endpoint
        self.endpoint_configs: Dict[Optional[str], APIConfig] = dict()
        self.endpoint_states: Dict[Optional[str], ClientState] = dict()

        self.endpoint_states[None] = self._initialize_client(api_config, session_config)
        self.endpoint_configs[None] = api_config

        self.display_progress_bar = display_progress_bar

        self.visited = set()
        self.tasks = []

    @classmethod
    def from_config(cls, api_config: APIConfig, session_config: SessionConfig = SessionConfig()):
        """
        Creates an instance of the BaseClient class using API and Session configurations.

        Args:
            api_config (APIConfig): Configuration for the API client.
            session_config (SessionConfig, optional): Configuration for the session. Defaults to SessionConfig().

        Returns:
            BaseClient: Instance of the BaseClient class.
        """

        return BaseClient(
            **api_config.to_dict(),
            **session_config.to_dict()
        )

    def _get_client(self, endpoint: Optional[str] = None):
        """
        Retrieves the client associated with the specified endpoint.

        Args:
            endpoint (Optional[str], optional): The endpoint for which to get the client. Defaults to None.

        Returns:
            Client: The client associated with the specified endpoint.
        """

        return self.endpoint_states[endpoint].client

    def _initialize_client(self, api_config: APIConfig,
                           session_config: Optional[SessionConfig] = None):
        """
        Initializes a new client using the specified API and Session configurations.

        Args:
            api_config (APIConfig): Configuration for the API client.
            session_config (Optional[SessionConfig], optional): Configuration for the session. Defaults to None.

        Returns:
            ClientState: A state object representing the client's state.
        """

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

        if not self.endpoint_states or session_config is not None:
            if session_config is None:  # initialization of main client
                session_config = SessionConfig()
            client = RetryClient(
                retry_options=api_config.retry_options,
                logger=self.logger,
                **session_config.to_dict(),
            )
            self.clients.append(client)
        else:
            client = self.get_state(api_config.base_url).client

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
                     auth=None, connector=None, cookie_jar=None, cookies=None, headers=None, trust_env=None,
                     api_config: Optional[APIConfig] = None, session_config: Optional[SessionConfig] = None):
        """
        Adds settings to the client for a specific base URL. Overwrites the settings if they are already configured.

        """
        base_url = urlparse(url).netloc
        if base_url in self.endpoint_configs:
            if error_strategy is None:
                error_handling_strategy = self.get_config().error_strategy
            else:
                error_handling_strategy = error_strategy
            raise_exception(f"Base URL {base_url} has already been configured, overwriting settings...",
                            error_strategy=error_handling_strategy, exception_type='warning',
                            logger=self.logger)

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
        session_settings = [auth, connector, cookie_jar, cookies, headers, trust_env]
        if all(x is None for x in session_settings) and session_config is None:
            self.endpoint_states[base_url] = self._initialize_client(api_config)
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
        if trust_env is not None:
            session_config.trust_env = trust_env
        self.endpoint_states[base_url] = self._initialize_client(api_config)

    @staticmethod
    async def _sleep_for_rate_limit(state: ClientState, api_key=None):
        """
        Causes the calling coroutine to sleep for the appropriate amount of time to respect rate limits.

        Args:
            state (ClientState): The state of the client.
            api_key (str, optional): The API key to consider for rate limiting. Defaults to None.
        """
        semaphore = state.semaphores[api_key]
        async with semaphore:
            last_request_time = state.last_request_time[api_key]
            elapsed = time.monotonic() - last_request_time
            if state.wait_time > 0 and (sleep_time := max(state.wait_time - elapsed, 0)) > 0:
                await asyncio.sleep(sleep_time)
            state.last_request_time[api_key] = time.monotonic()

    @staticmethod
    def get_hash(method: str, url: str, hash_items: Optional[Any]):
        """
        Returns a hash value for the given method, URL, and hash items.
        This will help the API client know which APIs have been requested before and skip those.

        Args:
            method (str): The request method.
            url (str): The request URL.
            hash_items (dict): Additional items to include in the hash.

        Returns:
            int: The hash value.
        """
        return hash(hash(method) + hash(url) + hash(hash_items))

    @abstractmethod
    async def request_callback(self, result: Response, setup_info):
        """
        Abstract method that must be overridden in derived classes. Called after a request has been made.

        Args:
            result (Response): The result of the request.
            setup_info (Any): Setup information for the request.
        """
        yield

    async def make_request_setup(self, url: str) -> Any:
        """
        Setup method to be overridden in derived classes. Called before a request is made.

        Args:
            url (str): The URL of the request.

        Returns:
            Any: Returns anything.
        """
        pass

    async def make_request_cleanup(self, url: str, setup_info):
        """
        Cleanup method to be overridden in derived classes. Called after a request is made.

        Args:
            url (str): The URL of the request.
            setup_info (Any): Setup information for the request.
        """
        pass

    def setup_request(self, url: str, headers: dict, data: dict, setup_info: Any):
        """
        Setup method to be overridden in derived classes. Called before a request is made.

        Args:
            url (str): The URL of the request.
            headers (dict): Headers for the request.
            data (dict): Data to be sent with the request.
            setup_info (Any): Setup information for the request.
        """
        pass

    def get_state(self, url: str) -> ClientState:
        """
        Returns the state of the endpoint.

        Args:
           url (str): The URL of the endpoint.

        Returns:
           ClientState: The state of the endpoint.
        """
        if (base_url := urlparse(url).netloc) in self.endpoint_states:
            return self.endpoint_states[base_url]
        else:
            return self.endpoint_states[None]

    def get_config(self, url: Optional[str] = None) -> APIConfig:
        """
        Returns the configuration for the endpoint.

        Args:
            url (str, optional): The URL of the endpoint.

        Returns:
            APIConfig: The configuration for the endpoint.
        """
        if url is not None and (base_url := urlparse(url).netloc) in self.endpoint_configs:
            return self.endpoint_configs[base_url]
        else:
            return self.endpoint_configs[None]

    async def _make_request(self, method: str, url: str, data: dict = None, kwargs: dict = None):
        """
        Sends a request to a URL and handles the response.

        Args:
            method (str): The HTTP method (GET or POST).
            url (str): The URL of the endpoint.
            data (dict, optional): A dictionary containing the request data.
            kwargs (dict, optional): A dictionary containing additional parameters.
                This includes information such as proxies, proxy authentication, and SSL verification information.
        """
        new_requests = []

        # Setup headers
        headers = {}
        data = data or {}
        kwargs = kwargs or {}

        setup_info = await self.make_request_setup(url)
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
        self.stats.add_request(parsed_url.netloc, method)

        try:
            async with state.client.request(
                    method, url, headers=headers, **request_params, timeout=config.timeout, **kwargs) as response:
                self.stats.add_response(response)
                response_result = Response(response, config, state, self.logger)
                async for result in self.request_callback(response_result, setup_info):
                    if result is None:
                        continue
                    response_type, content = result
                    if response_type != ResponseType.REQUEST:
                        continue
                    new_method, new_url, new_data, new_settings = content
                    new_parsed_url = urlparse(new_url)
                    if len(new_parsed_url.netloc) == 0:
                        # noinspection PyProtectedMember
                        new_parsed_url = new_parsed_url._replace(scheme=parsed_url.scheme, netloc=parsed_url.netloc)
                        new_url = urlunparse(new_parsed_url)
                    new_requests.append((new_method, new_url, new_data, new_settings))
        except asyncio.TimeoutError as e:
            self.stats.timeouts += 1
            self.logger.error(
                {"message": "request_failed", "method": method, "url": url, "data": data, "error": str(e)})
        except aiohttp.ClientResponseError as e:
            self.logger.error(
                {"message": "request_failed", "method": method, "url": url, "data": data, "error": str(e)})
        except aiohttp.ClientConnectorError as e:
            self.stats.add_network_error()
            self.logger.error(
                {"message": "failed_connection", "method": method, "url": url, "data": data, "error": str(e)})
        finally:
            await self.make_request_cleanup(url, setup_info)
            for new_method, new_url, new_data, new_settings in new_requests:
                for method, url, data, kwargs in self._package_requests(new_method, new_url, new_data, new_settings):
                    self.tasks.append(asyncio.create_task(self._get_request_handler(method)(url, data, kwargs)))

    async def _get(self, url: str, params: dict = None, kwargs: dict = None):
        """
        Sends a GET request to a URL and handles the response.

        Args:
            url (str): The URL of the endpoint.
            params (dict, optional): A dictionary containing the request parameters.
            kwargs (dict, optional): A dictionary containing additional parameters.
        """
        await self._make_request("GET", url, data=params, kwargs=kwargs)

    async def _post(self, url: str, data: dict = None, kwargs: dict = None):
        """
        Sends a POST request to a URL and handles the response.

        Args:
            url (str): The URL of the endpoint.
            data (dict, optional): A dictionary containing the request data.
            kwargs (dict, optional): A dictionary containing additional parameters.
        """
        await self._make_request("POST", url, data=data, kwargs=kwargs)

    def _get_request_handler(self, method) -> Callable[[str, dict, dict], Coroutine]:
        """
        Returns the appropriate request handler based on the method.

        Args:
            method (str): The HTTP method (GET or POST).

        Returns:
            Callable[[str, dict, dict], Coroutine]: The request handler function.

        Raises:
            ValueError: If the method is not GET or POST.
        """
        method = method.upper()
        if method == 'GET':
            return self._get
        elif method == 'POST':
            return self._post
        else:
            raise ValueError("Method must be either GET or POST!")

    @staticmethod
    def _package_requests(methods: StringSequence, endpoints: StringSequence,
                          data_list: OptionalDictSequence, settings: OptionalDictSequence):
        """
        Packages the request details for multiple requests.

        Args:
            methods (StringSequence): The HTTP methods for the requests.
            endpoints (StringSequence): The endpoints for the requests.
            data_list (OptionalDictSequence): The data for the requests.
            settings (OptionalDictSequence): The settings for the requests.

        Yields:
            tuple: The details for each request.
        """
        methods = [methods] if isinstance(methods, str) else methods
        endpoints = [endpoints] if isinstance(endpoints, str) else endpoints
        data_list = [data_list] if isinstance(data_list, dict) or data_list is None else data_list
        settings = [settings] if isinstance(settings, dict) or settings is None else settings

        max_length = max(len(methods), len(endpoints), len(data_list), len(settings))
        assert {len(methods), len(endpoints), len(data_list)}.issubset({1, max_length})

        methods = cycle(methods)
        endpoints = cycle(endpoints)
        data_list = cycle(data_list)
        settings = cycle(settings)

        for _ in range(max_length):
            yield next(methods), next(endpoints), next(data_list), next(settings)

    async def execute_requests(self,
                               methods: StringSequence,
                               urls: StringSequence,
                               data_list: OptionalDictSequence,
                               settings: OptionalDictSequence):
        """
        Executes the requests. Displays a progress bar if `self.display_progress_bar` is set to True.

        Args:
            methods (StringSequence): The HTTP methods for the requests.
            urls (StringSequence): The endpoints for the requests.
            data_list (OptionalDictSequence): The data for the requests.
            settings (OptionalDictSequence): The settings for the requests.
        """

        tasks = [asyncio.create_task(self._get_request_handler(method)(endpoint, data, s))
                 for method, endpoint, data, s in self._package_requests(methods, urls, data_list, settings)]
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

    async def run(self,
                  methods: StringSequence,
                  urls: StringSequence,
                  data_list: OptionalDictSequence = None,
                  settings: OptionalDictSequence = None):
        """
        Runs the client with the provided request details.

        Args:
            methods (StringSequence): The HTTP methods for the requests.
            urls (StringSequence): The endpoints for the requests.
            data_list (OptionalDictSequence, optional): The data for the requests.
            settings (OptionalDictSequence, optional): The settings for the requests.
        """
        await self.execute_requests(methods, urls, data_list, settings)

    async def get(self, urls: StringSequence,
                  data_list: OptionalDictSequence = None,
                  settings: OptionalDictSequence = None):
        """
        Runs the client with the GET method.

        Args:
            urls (StringSequence): The endpoints for the requests.
            data_list (OptionalDictSequence, optional): The data for the requests.
            settings (OptionalDictSequence, optional): The settings for the requests.
        """
        await self.run("GET", urls, data_list, settings)

    async def post(self, urls: StringSequence,
                   data_list: OptionalDictSequence = None,
                   settings: OptionalDictSequence = None):
        """
        Runs the client with the POST method.

        Args:
            urls (StringSequence): The endpoints for the requests.
            data_list (OptionalDictSequence, optional): The data for the requests.
            settings (OptionalDictSequence, optional): The settings for the requests.
        """
        await self.run("POST", urls, data_list, settings)

    async def __aenter__(self):
        """
        Defines what the context manager should do at the beginning of the block.

        Returns:
            BaseClient: Returns an instance of the API Client.
        """
        return self

    async def __aexit__(self, *args):
        """
        Defines what the context manager should do at the end of the block.

        Args:
            *args: Dummy arguments to match signature of the __aexit__ protocol.
        """
        for client in self.clients:
            await client.close()
        logging.info(self.stats.get_stats())
