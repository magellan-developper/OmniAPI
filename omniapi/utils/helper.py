import datetime
import json
import logging
from pathlib import Path
from typing import Union, Sequence, Optional

import aiofiles

from omniapi.utils.config import APIConfig
from omniapi.utils.exception import raise_exception


def get_single_wait_time(max_requests_per_interval: Union[int, float],
                         interval: datetime.timedelta) -> float:
    """Gets the wait time, given a max_requests_per_interval and interval.
        If max_requests_per_interval is 0 or negative, the function returns a wait time of 0.

    Args:
        max_requests_per_interval (Union[int, float]): The directory path where the file should be downloaded.
        interval (datetime.timedelta): Number of requests allowed per interval

    Returns:
        (float): Total number of seconds to wait
    """
    if max_requests_per_interval <= 0:
        return 0
    return interval.total_seconds() / max_requests_per_interval


def get_wait_time(config: APIConfig,
                  logger: Optional[logging.Logger] = None) -> float:
    """Gets the maximum wait time, given a series of max_request_per_interval and interval_unit.
        If both max_requests_per_interval and interval_unit are lists / tuples, they must have the same length.

    Args:
        config (APIConfig): Config of API Client
        logger (Logger): Logger for logging errors if logging exceptions

    Returns:
        (float): Maximum wait time in seconds
    """
    max_requests_per_interval = config.max_requests_per_interval
    interval_unit = config.interval_unit
    error_strategy = config.error_strategy

    if isinstance(max_requests_per_interval, Sequence) and len(max_requests_per_interval) == 0:
        raise_exception("Length of max_requests_per_interval must not be 0", error_strategy, logger=logger)
    if isinstance(interval_unit, Sequence) and len(interval_unit) == 0:
        raise_exception("Length of interval_unit must not be 0", error_strategy, logger=logger)

    if isinstance(max_requests_per_interval, Sequence) and isinstance(interval_unit, Sequence):
        if len(max_requests_per_interval) != len(interval_unit):
            raise_exception(f"Length Mismatch: Length of max_requests_per_interval ({len(max_requests_per_interval)})"
                            f" != interval_unit ({len(interval_unit)})", error_strategy, logger=logger)
        return max(get_single_wait_time(max_request, unit) for max_request, unit in
                   zip(max_requests_per_interval, interval_unit))
    if isinstance(max_requests_per_interval, Sequence):
        return max(get_single_wait_time(max_request, interval_unit) for max_request in max_requests_per_interval)
    if isinstance(interval_unit, Sequence):
        return max(get_single_wait_time(max_requests_per_interval, unit) for unit in interval_unit)
    return get_single_wait_time(max_requests_per_interval, interval_unit)


async def write_json(path: Path, data):
    """
    Asynchronously writes JSON data to a file.

    Args:
        path (Path): The path of the file where the JSON data should be written.
        data (Any): The data to be written in JSON format.
    """
    async with aiofiles.open(path, mode='w') as f:
        await f.write(json.dumps(data))
