# OmniAPI - APIs Simplified

## Testing Procedure
1. Try to look for an API that you are interested in. You can explore some options [here](https://rapidapi.com/hub) for more API endpoints. We want to test the library on diverse endpoints to make sure that it fits the general user's needs.
2. Install OmniAPI locally, along with its dependencies. 
3. Try to fetch and store the contents of your chosen API. You can store it as a file using `JsonFileClient`, or by extending `APIClient` and overloading the `process_request` or `request_callback` function (more details below).
4. Provide some feedback on this [survey](https://docs.google.com/forms/d/e/1FAIpQLSfdvYKFT71-GjO-5PtQxAZ7LRG2oMHJ5NuD3cfX-I0RUjH8HA/viewform?usp=pp_url).

## Example
Here is an example that walks through the process above using an API that fetches details for Pokémon. 

### Step 1: Choose an API Endpoint
Let us fetch data from the Pokémon API, specifically the endpoint that provides information about Bulbasaur. You can find this API [here](https://pokeapi.co/api/v2/pokemon/1).

### Step 2: Install OmniAPI and Dependencies
Before using OmniAPI, you must install it on your system along with its dependencies. It is recommended to use a virtual environment so that it doesn't affect your other dependencies.

```bash
git clone https://github.com/magellan-developper/OmniAPI.git
cd OmniAPI
# python -m venv venv
# source venv/bin/activate
# pip install wheel
pip install -r requirements.txt
pip install -e .
```

### Step 3: Fetch and Store Content from the Pokémon API
You can fetch and store the contents of the Pokémon API using OmniAPI's `JsonFileClient`. Below is the code snippet that demonstrates how to do this.

```python
from omniapi import JsonFileClient

async with JsonFileClient(export_results_path='file.json', max_requests_per_interval=5) as client:
    await client.get('https://pokeapi.co/api/v2/pokemon/1')
```

**Important:** To run the client directly in a file, you can wrap it in a function and pass it to asyncio.run().

```python
import asyncio
from omniapi import JsonFileClient

async def fetch_api():
    async with JsonFileClient(export_results_path='file.json', max_requests_per_interval=5) as client:
        await client.get('https://pokeapi.co/api/v2/pokemon/1')

asyncio.run(fetch_api())
```

### Extending `APIClient`

You can override the `process_request` function to control what you want to do with the fetched data. The response_type returned by get_result_content will be either JSON, TEXT, or FILE depending on the content-type of the response.
Depending on the `response_type`, the returned content will be one of the following items.
- `response_type` is a JSON: Dictionary containing the JSON contents
- `response_type` is TEXT: The text response in string
- `response_type` is FILE: If `files_download_directory` is set, the file will be downloaded and `content` will be a dictionary containing the url, downloaded path, and checksum of the file. Otherwise, `content` will be None.

If you need access to the response object (ex. getting information on the URL), you can instead override the `request_callback` function, which is a wrapper around `process_request` to call the `get_result_content` function on the fetched result automatically.

Let us try to customize the processing of the request. Instead of fetching only the first id, let us do an "API request chaining" to fetch data from ids 1 - 10.
In practice, you can use this method, to recursively fetch data from an entire website with minimal code, or download files and images from a URL in the returned response.

```python
from omniapi import APIClient, Response


class CustomAPIClient(APIClient):
    async def request_callback(self, response: Response, setup_info):
        response_type, content = await self.get_result_content(response)

        url = response.get_url()
        index = url.rindex('/')
        page_id = int(url[index + 1:])
        if page_id < 10:
            new_url = f'{url[:index]}/{page_id + 1}'
            yield response.get(new_url)

        print(response.get_url())


# Usage
async with CustomAPIClient(max_requests_per_interval=5) as client:
    await client.get('https://pokeapi.co/api/v2/pokemon/1')
```

### Step 4: Provide Feedback
After working with the Pokémon API using OmniAPI, you can provide feedback on the experience by filling out the specified survey.

And that's it! This example guides you through using OmniAPI to interact with the Pokémon API, fetch and store data about Bulbasaur, and optionally extend the processing functionality.

## More details on OmniAPI

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

## BaseClient and Derived Classes

OmniAPI provides you with a flexible and customizable structure. It comes with a `BaseClient` class and several subclasses, `APIClient` and `JsonFileClient`, each of which provides distinct functionalities tailored to different use cases.

### BaseClient

`BaseClient` is the abstract base class that forms the foundation for other API clients in OmniAPI. It outlines the generic functionalities and protocols required by any client, ensuring a consistent API across all subclasses.

### APIClient

`APIClient` is a base class derived from `BaseClient`. It includes core API request functionalities including handling request setup, response content extraction and request cleanup. 

To utilize this class, you need to inherit from the `APIClient` and implement the `request_callback` method. The `request_callback` method is where you define what happens after each API request. For instance, in the `JsonFileClient`:

```python
from omniapi import ResponseType


async def process_request(self, response_type: ResponseType, content):
    # Your custom processing code here

    yield response_type, content
```

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
