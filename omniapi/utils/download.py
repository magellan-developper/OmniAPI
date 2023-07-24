import hashlib
import logging
import mimetypes
import uuid
import os
from yarl import URL
from pathlib import Path
from typing import Union, Optional

import aiofiles

from enum import Enum, auto
from urllib.parse import unquote_to_bytes, urlparse

from aiohttp.client_reqrep import ClientResponse
from omniapi.utils.exception import raise_exception


class FileNameMode(Enum):
    UNIQUE_ID = auto()
    FILE_NAME = auto()
    URL_HASH_MD5 = auto()
    URL_HASH_SHA1 = auto()


def get_file_name(url: Union[str, URL], strategy: FileNameMode):
    """

    :param url:
    :param strategy:
    :return:
    """
    url = str(url)
    if strategy == FileNameMode.UNIQUE_ID:
        return str(uuid.uuid4())
    elif strategy == FileNameMode.URL_HASH_MD5:
        return hashlib.md5(unquote_to_bytes(url)).hexdigest()
    elif strategy == FileNameMode.URL_HASH_SHA1:
        return hashlib.sha1(unquote_to_bytes(url)).hexdigest()
    elif strategy == FileNameMode.FILE_NAME:
        return os.path.basename(url)
    else:  # TODO
        raise ValueError("Invalid strategy chosen!")


async def download_file(response: ClientResponse,
                        filename: Union[Path, str],
                        chunk_size: int = 1024):
    """Downloads the contents of a response to a file named `filename` and returns the md5 hash of the file.

    :param response: Response of download request
    :param filename: Name of downloaded file
    :param chunk_size: Size of download chunk
    :return: MD5 Hash of downloaded file
    """
    hash_obj = hashlib.md5()
    async with aiofiles.open(filename, 'wb') as out_file:
        async for chunk in response.content.iter_chunked(chunk_size):
            await out_file.write(chunk)
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def get_file_extension(response: ClientResponse,
                       logger: Optional[logging.Logger] = None) -> Optional[str]:
    """Guesses the file extension based on the Content-Type and url of the response.

    :param response: Response of request to download object
    :param logger: Logger of API Client
    :return: File extension of the download response. Returns None if the type can't be guessed.
    """
    if 'Content-Type' in response.headers:
        content_type = response.headers['Content-Type']
        extension = mimetypes.guess_extension(content_type)
        if extension:
            return extension
        else:
            raise_exception(
                f"Extension of Content-Type {content_type} not recognized!",
                exception_type='warning',
                logger=logger
            )  # TODO
    path = urlparse(response.url.path).path
    extension = Path(path).suffix
    if extension:
        return extension
    return None


def get_file_path(response: ClientResponse,
                  download_directory: Path,
                  naming_strategy: FileNameMode,
                  logger: Optional[logging.Logger] = None) -> Path:
    """Gets the download path of the file from the response.
        Creates the parent directories if they do not exist.

    :param response: Response of download request
    :param download_directory: Directory to download files
    :param naming_strategy:
    :param logger:
    :return:
    """
    if isinstance(download_directory, str):
        download_directory = Path(download_directory)
        download_directory.mkdir(exist_ok=True, parents=True)
    file_name = Path(get_file_name(response.url, naming_strategy))
    file_extension = get_file_extension(response, logger)
    file_path = file_name.with_suffix(file_extension)
    file_path = download_directory / file_path
    if file_path.exists():  # TODO
        raise_exception(f"Overwriting existing file {file_path}", exception_type='warning', logger=logger)
    return file_path


async def download_file_to_path(response: ClientResponse,
                                download_directory: Union[Path, str],
                                naming_strategy: FileNameMode,
                                logger: Optional[logging.Logger] = None):
    """

    :param response:
    :param download_directory:
    :param naming_strategy:
    :param logger:
    :return:
    """
    download_directory = Path(download_directory)
    file_path = get_file_path(response, download_directory, naming_strategy, logger)
    checksum = await download_file(response, file_path)
    file_path = file_path.relative_to(download_directory)
    return {
        "url": str(response.url),
        "path": file_path,
        "checksum": checksum,
    }
