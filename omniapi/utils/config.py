import datetime
from abc import ABCMeta
from dataclasses import dataclass, asdict
from enum import Enum, auto
from typing import Optional, Sequence, Union
from urllib.parse import urlparse

from aiohttp import BasicAuth, BaseConnector
from aiohttp.abc import AbstractCookieJar
from aiohttp_retry import RetryOptionsBase

from omniapi.utils.types import PathType
from omniapi.utils.types import numeric


class FileNameStrategy(Enum):
    """Enum for different file naming strategies."""

    UNIQUE_ID = auto()
    FILE_NAME = auto()
    URL_HASH_MD5 = auto()
    URL_HASH_SHA1 = auto()


@dataclass
class BaseConfig(metaclass=ABCMeta):
    """
    Base configuration class, to be inherited by specific configuration classes.
    Contains a method to convert configuration object to a dictionary.
    """

    def to_dict(self):
        """Convert the dataclass to a dictionary."""
        return asdict(self)


@dataclass
class APIConfig(BaseConfig):
    """Configuration for an API client."""
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
    file_name_mode: FileNameStrategy = FileNameStrategy.URL_HASH_MD5

    # User Settings
    display_progress_bar: bool = False


@dataclass
class SessionConfig(BaseConfig):
    """Configuration for a session."""

    auth: Optional[BasicAuth] = None
    connector: Optional[BaseConnector] = None
    cookie_jar: Optional[AbstractCookieJar] = None
    cookies: Optional[dict] = None
    headers: Optional[dict] = None
    trust_env: bool = False
