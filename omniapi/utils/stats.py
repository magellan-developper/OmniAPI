import time
from collections import Counter
from dataclasses import dataclass, field

from aiohttp.client import ClientResponse


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
    rate_limit_exceeded: int = 0

    start_time: float = time.time()

    content_types: Counter = field(default_factory=Counter)
    endpoint_count: Counter = field(default_factory=Counter)
    status_codes: Counter = field(default_factory=Counter)
    method_count: Counter = field(default_factory=Counter)

    def add_request(self, netloc: str, method: str):
        self.total_requests += 1
        self.method_count.update([method])
        self.endpoint_count.update([netloc])

    def add_response(self, response: ClientResponse):
        self.add_status_code(response.status)

        if 'Content-Type' in response.headers:
            self.content_types.update([response.headers['Content-Type']])

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

    def add_network_error(self):
        self.network_errors += 1

    @property
    def total_errors(self):
        return self.client_errors + self.server_errors + self.network_errors + self.timeouts

    @property
    def error_rate(self):
        return self.total_errors / self.total_requests

    @property
    def total_time(self):
        return time.time() - self.start_time

    def get_stats(self):
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
                'Endpoint Count': self.endpoint_count,
                'Content Types': self.content_types,
                'Status Codes': self.status_codes,
                'Request Methods': self.method_count
                }
