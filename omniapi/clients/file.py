from pathlib import Path

from omniapi.clients.api import APIClient
from omniapi.utils.helper import write_json
from omniapi.utils.result import Result, ResultType
from omniapi.utils.types import StringSequence, OptionalDictSequence


class JsonFileClient(APIClient):
    """
    Class to download API content and store the results in a JSON file.
    The JSON file is organized into 3 sections: json, text, and file.
    The `json` and `text` sections store responses with JSON and TEXT type.
    The `file` section stores the url, file path, and checksum of the files downloaded.

    Attributes:
    export_results_path (str): The path where the results will be exported as a JSON file.
    results (dict): A dictionary that stores the results.

    """

    def __init__(self, export_results_path: str, *args, **kwargs):
        """
        Initialize a new instance of JsonFileClient

        Args:
        export_results_path (str): The path where the results will be exported as a JSON file.
        *args: Args to pass to API Client
        **kwargs: Kwargs to pass to API Client

        """
        super().__init__(*args, **kwargs)
        self.export_results_path = export_results_path
        self.results = {ResultType.JSON.name.lower(): [],
                        ResultType.TEXT.name.lower(): [],
                        ResultType.FILE.name.lower(): []}

    async def request_callback(self, result: Result, _):
        """
        Callback function for request. It gets the content of the result
        and appends it to the corresponding section of the results.

        Args:
        result (Result): The result object.

        Returns:
        Tuple[ResultType, Any]: The result type and content.

        """

        result_type, content = await self.get_result_content(result)
        if result_type in [ResultType.JSON, ResultType.TEXT, ResultType.FILE]:
            key = result_type.name.lower()
            self.results[key].append(content)
        yield result_type, content

    async def export_results(self):
        """
        Export the results to a JSON file. If the file already exists, it will be overwritten.

        """

        export_path = Path(self.export_results_path)
        if export_path.exists():
            self.logger.error(f"File {export_path} already exists! Overwriting file...")
        export_path.parent.mkdir(exist_ok=True, parents=True)
        await write_json(export_path, self.results)

    async def run(self,
                  methods: StringSequence,
                  urls: StringSequence,
                  data_list: OptionalDictSequence = None,
                  settings: OptionalDictSequence = None):
        """
        Runs the client and exports the results to a JSON file

        Args:
        methods (StringSequence): The HTTP method(s) for the request(s).
            Can be a single string (e.g., 'GET', 'POST') or a sequence of such strings.
        urls (StringSequence): The urls for the request(s).
            Can be a single string (e.g., 'https://example.com/api') or a sequence of such strings.
        data_list (OptionalDictSequence, optional): The data to be included in the request(s).
            It can be None, a single dictionary, or a sequence of dictionaries. Defaults to None.
        settings (OptionalDictSequence, optional): Settings for the request(s).
           It can be None, a single dictionary, or a sequence of dictionaries. Defaults to None.
        """

        await self.schedule_requests(methods, urls, data_list, settings)
        await self.export_results()
