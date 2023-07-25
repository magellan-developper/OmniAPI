# OmniAPI - APIs Simplified

## Introduction

OmniAPI is a sophisticated API client library designed to streamline and manage the interaction between your application and various APIs. It provides asynchronous processing support, extensive customization options, and robust error handling capabilities. OmniAPI comes with a rich feature set that allows fine-grained control over your API requests, and enables detailed reporting of API performance metrics.

## Features

OmniAPI includes a vast range of features that optimize and simplify your API interactions:

- **API Key Management**: Handle rate limits and manage API keys efficiently.
- **Easy Configuration**: Customize parameters for more precise control over requests.
- **Error Handling & Reporting**: Log errors and utilize built-in retry mechanisms.
- **HTTP Methods Support**: GET and POST methods.
- **Pagination Handling**: Simplifies interactions with paginated API responses.
- **Timeouts & Connection Handling**: Manage connections and control request timeouts.
- **Authentication**: Supports various authentication methods.
- **Logging**: Log requests and responses for debugging or analysis.
- **Throttling**: Control the request frequency to avoid overloading APIs.
- **Automatic Backoff**: Implement backoff algorithms for better error recovery.
- **Database Connection**: Connect your API client with database systems.
- **Bulk / Batch Requests**: Efficiently handle multiple requests at once.
- **Multi-part Form Data**: Support for sending form data.
- **Proxy Support**: Utilize proxies for requests.
- **Cookies & Session Handling**: Manage cookies and sessions easily.
- **Automatic Redirects**: Handle redirects seamlessly.
- **SSL / TLS Verification**: Ensure secure communications.
- **Connection Pooling**: Improve performance through connection reuse.
- **API Endpoint Discovery**: Discover API endpoints automatically.
- **Content Type Negotiation**: Choose the right content type for your requests.
- **Session Management**: Control sessions for better resource utilization.
- **Custom Headers Support**: Add custom headers to requests.
- **API Website Connection**: Connect directly with API websites.

## Quickstart

```python
from omniapi import JsonFileClient

async with JsonFileClient(max_requests_per_interval=5) as client:
    await client.get('https://pokeapi.co/api/v2/pokemon/1')
```
Certainly, here's a more detailed installation guide:

## Installation

To install `omniapi`, you can use Python's package installer `pip`. Follow the steps below to install `omniapi`:

1. Install the package by running the following command:

    ```bash
    pip install omniapi
    ```
2. Verify that `omniapi` has been installed successfully by checking its version:

    ```bash
    python -c "import omniapi; print(omniapi.__version__)"
    ```

In case you encounter any issues during installation, feel free to open an issue on the GitHub repository or reach out through the listed support channels.

## BaseClient and Derived Classes

OmniAPI provides you with a flexible and customizable structure. It comes with a `BaseClient` class and several subclasses, `APIClient` and `JsonFileClient`, each of which provides distinct functionalities tailored to different use cases.

### BaseClient

`BaseClient` is the abstract base class that forms the foundation for other API clients in OmniAPI. It outlines the generic functionalities and protocols required by any client, ensuring a consistent API across all subclasses.

### APIClient

`APIClient` is a base class derived from `BaseClient`. It includes core API request functionalities including handling request setup, response content extraction and request cleanup. 

To utilize this class, you need to inherit from the `APIClient` and implement the `request_callback` method. The `request_callback` method is where you define what happens after each API request. For instance, in the `JsonFileClient`:

```python
async def request_callback(self, result: Result, _):
    # Fetch the content type and data from the result
    result_type, content = await self.get_result_content(result)

    # Do something
    
    # Return the result type and content for further processing
    yield result_type, content
```

The `get_result_content` method automatically determines the result's content type (JSON, TEXT, FILE) and extracts the corresponding data. Depending on the type, it returns the result type and content for any further procedures you might want to perform, e.g. saving to database.

### JsonFileClient

`JsonFileClient` extends the `APIClient` and includes added functionalities tailored for fetching API content and storing the results in a JSON file. The results are classified into three sections: `json`, `text`, and `file`.

#### Example

To use the `JsonFileClient`, you would create an instance of the client and call the `run()` method with the appropriate parameters, as demonstrated below:

```python
from omniapi import JsonFileClient

async with JsonFileClient(export_results_path='path/to/export') as client:
    await client.run('GET', 'https://pokeapi.co/api/v2/pokemon/1')
```

The JsonFileClient also provides convenience methods for two common HTTP requests: GET and POST.

The `JsonFileClient` provides convenience methods for two common HTTP requests: GET and POST.

- The `get()` method simplifies fetching data from a provided API endpoint.

```python
from omniapi import JsonFileClient

export_results_path='path/to/export'

client = JsonFileClient(export_results_path)
await client.get('https://pokeapi.co/api/v2/pokemon/1')
```

- Similarly, the `post()` method allows for effortless data sending to an API, with the response stored in an organized JSON file.

This will run the API requests and store the results in the designated JSON file. Note: The `export_results_path` should be replaced with the actual path where you want the JSON file to be saved.

## Constructor Parameters

You can use the following parameters in the constructor to adjust OmniAPI to your needs:

- `max_requests_per_interval`: Set the maximum requests per time interval (defaults to 5).
- `interval_unit`: Define the time unit for request intervals (defaults to 1 second).
- `max_concurrent_requests`: Set the maximum number of concurrent requests (defaults to 1).
- `api_keys`: Provide a list of API keys.
- `allow_redirects`: Allow HTTP redirects (defaults to True).
- `max_redirects`: Limit the maximum number of redirects (defaults to 0).
- `timeout`: Set a timeout for requests in seconds (defaults to 10.0).
- `files_download_directory`: Specify a directory for downloaded files.
- `file_name_mode`: Choose a file naming strategy (defaults to URL_HASH_MD5).
- `error_strategy`: Choose a strategy for handling errors (defaults to 'log').
- `display_progress_bar`: Enable or disable progress bar (defaults to False).
- `auth`: Provide basic authentication credentials.
- `connector`: Specify a custom connector.
- `cookie_jar`: Provide a custom cookie jar.
- `cookies`: Provide custom cookies.
- `headers`: Provide custom headers.
- `trust_env`: Trust environment variables for proxy configurations, SSL etc. (defaults to False).

## API Performance Metrics

OmniAPI allows tracking various API performance statistics:

- **Number of Requests**: Total count of API requests made.
- **Slowest Endpoints**: Identify slowest responding endpoints.
- **Response Times**: Record response times (Average, P95, P99, Min, Max).
- **Timeouts**: Track requests that are timing out.
- **Average Request Rate**: Measure requests per unit of time.
- **Error Rates**: Track error responses (4xx and 5xx).
- **Successful Requests**: Track successful responses (2xx).
- **API Usage by Method**: Breakdown of API usage by HTTP methods.
- **API Usage by Endpoint**: Frequency of endpoint usage.
- **Authentication Failures**: Track failed requests due to invalid credentials.
- **Rate Limit Exceeded**: Track requests that exceed API rate limits.
- **Redirects**: Count requests that resulted in HTTP redirects.
- **Network Errors**: Track errors related to network connectivity.
