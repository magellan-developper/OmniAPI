# OmniAPI

- API Key Management with Rate Limiting Awareness
- Easy Configuration
- Error Handling and Reporting
- HTTP Methods Support
- Data Serialization and Deserialization
- Pagination Handling
- Request Retry Mechanism
- Timeouts and Connection Handling
- Support for Various Authentication Methods
- Logging
- Throttling
- Asynchronous Processing Support
- Automatic Backoff
- Database Connection
- Bulk / Batch Requests
- Compression
- Multi-part Form Data
- Proxy Support
- Cookies and Session Handling
- Automatic Redirects
- SSL / TLS Verification
- Connection Pooling
- API Endpoint Discovery
- Content Type Negotiation
- Session Management
- Custom Headers Support
- Response Validation
- Middleware Support
- Connection with API websites

Stats
- Number of Requests: Track the total count of all types of API requests made.
- Slowest Endpoints: Identify endpoints that take the most time to respond.
- Response Times: Average, P95, P99, Min, and Max response times for API.
- Timeouts: The number of requests that are timing out.
- Average Request Rate: The number of requests per unit of time (e.g., requests per second).
- Error Rates: The number or percentage of requests that result in errors (4xx and 5xx responses).
- Successful Requests: The number or percentage of requests that are successful (2xx responses).
- API Usage by Method: The breakdown of API usage by the method used (GET, POST, PUT, DELETE, etc.)
- API Usage by Endpoint: Which endpoints are being used, and how frequently.
- API Key Usage: If you use multiple API keys, track usage per key to see if some are being used more than others.
- Authentication Failures: The number of requests that fail due to invalid credentials or tokens.
- Rate Limit Exceeded: The number of requests that exceed the rate limit of the API.
- Redirects: Count the number of requests that resulted in HTTP redirects.
- Network Errors: Any errors related to network connectivity should be tracked.
- Retry Counts: The number of requests that needed to be retried due to initial failure.

TODO:
- Fix aiohttp limit
- Fix client closing
