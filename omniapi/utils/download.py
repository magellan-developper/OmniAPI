"""Helper functions for downloading content"""

import hashlib
import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Union, Optional
from urllib.parse import unquote_to_bytes, urlparse

import aiofiles
from aiohttp.client_reqrep import ClientResponse
from yarl import URL

from omniapi.utils.config import APIConfig, FileNameStrategy
from omniapi.utils.exception import raise_exception


def get_file_name(url: Union[str, URL], strategy: FileNameStrategy):
    """Returns the name of the file to download based on the file name strategy chosen.

    :param url: Request URL
    :param strategy: File naming strategy
    :return: Download file name
    """
    url = str(url)
    if strategy == FileNameStrategy.UNIQUE_ID:
        return str(uuid.uuid4())
    elif strategy == FileNameStrategy.URL_HASH_MD5:
        return hashlib.md5(unquote_to_bytes(url)).hexdigest()
    elif strategy == FileNameStrategy.URL_HASH_SHA1:
        return hashlib.sha1(unquote_to_bytes(url)).hexdigest()
    elif strategy == FileNameStrategy.FILE_NAME:
        return os.path.basename(url)


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
                       error_handling_strategy: str,
                       logger: Optional[logging.Logger] = None) -> Optional[str]:
    """Returns the file extension based on the Content-Type and url of the response.

    :param response: Response of request to download object
    :param error_handling_strategy: Strategy to handle exception
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
                error_handling_strategy,
                exception_type='warning',
                logger=logger
            )
    path = urlparse(response.url.path).path
    extension = Path(path).suffix
    if extension:
        return extension
    return None


def get_file_path(response: ClientResponse,
                  config: APIConfig,
                  logger: Optional[logging.Logger] = None) -> Path:
    """Gets the download path of the file from the response.
        Creates the parent directories if they do not exist.

    :param response: Response of download request
    :param config:
    :param logger:
    :return:
    """
    download_directory = Path(config.files_download_directory)
    download_directory.mkdir(exist_ok=True, parents=True)
    file_name = Path(get_file_name(response.url, config.file_name_mode))
    file_extension = get_file_extension(response, config.error_strategy, logger)
    file_path = file_name.with_suffix(file_extension)
    file_path = download_directory / file_path
    if file_path.exists():
        raise_exception(f"Overwriting existing file {file_path}",
                        error_strategy=config.error_strategy,
                        exception_type='warning',
                        logger=logger)
    return file_path


async def download_file_to_path(response: ClientResponse,
                                config: APIConfig,
                                download_dir: Optional[Union[str, Path]] = None,
                                logger: Optional[logging.Logger] = None):
    """

    :param response:
    :param config:
    :param download_dir: Folder path relative to the files_download_directory to download content
    :param logger:
    :return:
    """
    base_dir = Path(config.files_download_directory)
    file_path = get_file_path(response, config, logger)
    if download_dir is not None:
        file_path = Path(download_dir) / file_path
    checksum = await download_file(response, file_path)
    file_path = file_path.relative_to(base_dir)
    return {
        "url": str(response.url),
        "path": file_path,
        "checksum": checksum,
    }
