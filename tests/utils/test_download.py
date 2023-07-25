import hashlib
import mimetypes
import os
from pathlib import Path

import pytest
from aiohttp.client_reqrep import ClientResponse

from omniapi.utils.config import APIConfig, FileNameStrategy
from omniapi.utils.download import get_file_name, download_file, get_file_extension, get_file_path


def test_get_file_name():
    url = 'http://example.com/myfile.png'

    assert len(get_file_name(url, FileNameStrategy.UNIQUE_ID)) == 36
    assert len(get_file_name(url, FileNameStrategy.URL_HASH_MD5)) == 32
    assert len(get_file_name(url, FileNameStrategy.URL_HASH_SHA1)) == 40
    assert get_file_name(url, FileNameStrategy.FILE_NAME) == 'myfile.png'


@pytest.mark.asyncio
async def test_download_file():
    data = b"fake data"
    response = ClientResponse("GET", "http://example.com")
    response.content = data
    filename = "test_file"
    expected_hash = hashlib.md5(data).hexdigest()

    actual_hash = await download_file(response, filename)
    assert actual_hash == expected_hash
    assert os.path.exists(filename)
    with open(filename, 'rb') as f:
        assert f.read() == data
    os.remove(filename)  # clean up


def test_get_file_extension():
    response = ClientResponse("GET", "http://example.com")
    response.headers["Content-Type"] = "image/png"
    assert get_file_extension(response, 'log') == mimetypes.guess_extension("image/png")


def test_get_file_path():
    response = ClientResponse("GET", "http://example.com/myfile.png")
    config = APIConfig()
    config.files_download_directory = "./"
    config.file_name_mode = FileNameStrategy.FILE_NAME
    path = get_file_path(response, config)
    assert path == Path('./myfile.png')
