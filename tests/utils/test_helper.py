import pytest
from omniapi.utils.config import APIConfig
from omniapi.utils.helper import get_single_wait_time, get_wait_time, write_json
from datetime import timedelta
import json
import os
import asyncio


def test_get_single_wait_time():
    max_requests_per_interval = 2
    interval = timedelta(minutes=1)
    assert get_single_wait_time(max_requests_per_interval, interval) == 30.0

    max_requests_per_interval = 0
    interval = timedelta(minutes=1)
    assert get_single_wait_time(max_requests_per_interval, interval) == 0


def test_get_wait_time():
    config = APIConfig()
    config.max_requests_per_interval = 2
    config.interval_unit = timedelta(minutes=1)
    assert get_wait_time(config) == 30.0

    config.max_requests_per_interval = [2, 3]
    config.interval_unit = [timedelta(minutes=1), timedelta(seconds=20)]
    assert get_wait_time(config) == 30.0

    config.max_requests_per_interval = 0
    config.interval_unit = timedelta(minutes=1)
    assert get_wait_time(config) == 0


@pytest.mark.asyncio
async def test_write_json():
    path = "./test.json"
    data = {"name": "test", "age": 25}
    await write_json(path, data)
    assert os.path.exists(path)
    with open(path, 'r') as f:
        assert json.load(f) == data
    os.remove(path)  # cleanup
