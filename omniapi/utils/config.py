import datetime
from abc import ABCMeta
from dataclasses import dataclass, asdict
from typing import Optional, Sequence, Union
from urllib.parse import urlparse

from aiohttp import BasicAuth, BaseConnector
from aiohttp.abc import AbstractCookieJar
from aiohttp_retry import RetryOptionsBase

from omniapi.utils.download import FileNameMode
from omniapi.utils.types import PathType
from omniapi.utils.types import numeric


@dataclass
class BaseConfig(metaclass=ABCMeta):
    def to_dict(self):
        return asdict(self)


@dataclass
class APIConfig(BaseConfig):
    _base_url: Optional[str] = None

    @property
    def base_url(self) -> Optional[str]:
        return self._base_url

    @base_url.setter
    def base_url(self, _base_url: Optional[str] = None):
        if _base_url is not None:
            self._base_url = urlparse(_base_url).netloc

    # Request Rate
    max_requests_per_interval: Union[Sequence[numeric], numeric] = 0
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
    trust_env: bool = False


@dataclass
class ClientConfig:
    api: APIConfig
    session: SessionConfig
