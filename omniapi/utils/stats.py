import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from aiohttp import TraceConfig
from aiohttp.client import ClientResponse


def calculate_percentile(lst: list, percentile: float):
    index = percentile * (len(lst) - 1)
    if index == int(index):
        return lst[int(index)]
    return (lst[int(index)] + lst[int(index) + 1]) / 2


def calculate_stats(lst: list[float], percentiles=(0.95, 0.99)):
    lst.sort()
    n = len(lst)
    mean = sum(lst) / n
    result = {'min': min(lst), 'mean': mean}
    for percentile in percentiles:
        result[f"{percentile * 100:g}%"] = calculate_percentile(lst, percentile)
    result['max'] = max(lst)
    return result


@dataclass
class ClientStats:
    total_requests: int = 0

    successful_requests: int = 0  # 2xx responses
    redirects: int = 0
    client_errors: int = 0  # 4xx errors
    server_errors: int = 0  # 5xx errors
    network_errors: int = 0  # connectivity errors, DNS errors

    timeouts: int = 0
    authentication_failure: int = 0
    retry_counts: int = 0
    rate_limit_exceeded: int = 0
    dns_cache_hit: int = 0

    start_time: float = time.time()
    response_times: dict = field(default_factory=dict)
    content_types: Counter = field(default_factory=Counter)
    status_codes: Counter = field(default_factory=Counter)
    api_key_usage: Counter = field(default_factory=Counter)
    method_api_usage: Counter = field(default_factory=Counter)

    def add_response(self, response: ClientResponse, api_key: Optional[str] = None):
        # self.add_status_code(response.status)
        self.add_method(response.method)
        if api_key:
            self.add_api_key(api_key)

    def add_status_code(self, status_code: int):
        self.status_codes.update([status_code])
        if (status_type := status_code // 100) == 2:
            self.successful_requests += 1
        elif status_type == 3:
            self.redirects += 1
        elif status_type == 4:
            self.client_errors += 1
        elif status_type == 5:
            self.server_errors += 1
        if status_code == 408:
            self.timeouts += 1
        elif status_code == 401:
            self.authentication_failure += 1
        elif status_code == 429:
            self.rate_limit_exceeded += 1

    def add_response_time(self, endpoint: str, response_time: float):
        if endpoint not in self.response_times:
            self.response_times[endpoint] = []
        self.response_times[endpoint].append(response_time)

    def add_method(self, method: str):
        self.method_api_usage.update([method])

    def add_api_key(self, api_key: str):
        self.api_key_usage.update([api_key])

    @property
    def total_errors(self):
        return self.client_errors + self.server_errors + self.network_errors

    @property
    def error_rate(self):
        return self.total_errors / self.total_requests

    @property
    def total_time(self):
        return time.time() - self.start_time

    def quick_stats(self):
        average_request_rate = self.total_time / self.total_requests
        return {'Total Requests': self.total_requests,
                'Average Request Rate': average_request_rate,
                'Successful Requests': self.successful_requests,
                'Total Errors': self.total_errors,
                'Redirect Counts': self.redirects,
                'Client Errors': self.client_errors,
                'Server Errors': self.server_errors,
                'Network Errors': self.network_errors,
                'Timeout Counts': self.timeouts,
                'Error Rates': self.error_rate,
                'DNS Cache Hit': self.dns_cache_hit}

    def full_stats(self):
        return {
            **self.quick_stats(),
            'Response Times': self.response_times,
            'Content Types': self.content_types,
            'Status Codes': self.status_codes,
            'API Key Usage': self.api_key_usage,
            'Request Methods': self.method_api_usage
        }


class StatsTraceConfig(TraceConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        stats = ClientStats()
    def on_request_start(self):
        pass
