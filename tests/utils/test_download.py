from omniapi.utils.config import FileNameStrategy
from omniapi.utils.download import get_file_name


def test_get_file_name():
    url = 'http://example.com/myfile.png'

    assert len(get_file_name(url, FileNameStrategy.UNIQUE_ID)) == 36
    assert len(get_file_name(url, FileNameStrategy.URL_HASH_MD5)) == 32
    assert len(get_file_name(url, FileNameStrategy.URL_HASH_SHA1)) == 40
    assert get_file_name(url, FileNameStrategy.FILE_NAME) == 'myfile.png'
