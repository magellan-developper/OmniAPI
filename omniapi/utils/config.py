import datetime
from abc import ABCMeta
from dataclasses import dataclass, asdict
from ssl import SSLContext
from typing import Optional, Sequence, Union

from aiohttp import BasicAuth, BaseConnector
from aiohttp.abc import AbstractCookieJar
from aiohttp_retry import RetryOptionsBase

from omniapi.utils.download import FileNameMode
from omniapi.utils.helper import numeric
from omniapi.utils.types import PathType


@dataclass
class BaseConfig(metaclass=ABCMeta):
    def to_dict(self):
        return asdict(self)


@dataclass
class APIConfig(BaseConfig):
    base_url: str

    # Request Rate
    max_requests_per_interval: Union[Sequence[numeric], numeric] = 5
    interval_unit: Union[Sequence[datetime.timedelta], datetime.timedelta] = datetime.timedelta(seconds=1)
    max_concurrent_requests: int = 1

    # Client Settings
    api_keys: Optional[Sequence[str]] = None
    allow_redirects: bool = True
    max_redirects: int = 0
    retry_options: Optional[RetryOptionsBase] = None
    timeout: float = 10.0
    error_strategy: str = 'log'

    # Export Results Path
    files_download_directory: PathType = None
    file_name_mode: FileNameMode = FileNameMode.URL_HASH_MD5

    # User Settings
    display_progress_bar: bool = False


@dataclass
class SessionConfig(BaseConfig):
    auth: Optional[BasicAuth] = None
    connector: Optional[BaseConnector] = None
    cookie_jar: Optional[AbstractCookieJar] = None
    cookies: Optional[dict] = None
    headers: Optional[dict] = None
    ssl: Optional[Union[bool, SSLContext]] = None
    trust_env: bool = False
    proxy: Optional[str] = None
    proxy_auth: Optional[BasicAuth] = None
    proxies: Optional[Sequence[str]] = None


@dataclass
class ClientConfig:
    api: APIConfig
    session: SessionConfig
