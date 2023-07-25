from pathlib import Path

from omniapi.clients.api import APIClient
from omniapi.utils.helper import write_json
from omniapi.utils.result import Result, ResultType
from omniapi.utils.types import StringSequence, OptionalDictSequence


class JsonFileClient(APIClient):
    def __init__(self, export_results_path: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.export_results_path = export_results_path
        self.results = {ResultType.JSON.name.lower(): [],
                        ResultType.TEXT.name.lower(): [],
                        ResultType.FILE.name.lower(): []}

    async def request_callback(self, result: Result, _):
        result_type, content = await self.get_result_content(result)
        if result_type in [ResultType.JSON, ResultType.TEXT, ResultType.FILE]:
            key = result_type.name.lower()
            self.results[key].append(content)
        yield result_type, content

    async def export_results(self):
        export_path = Path(self.export_results_path)
        if export_path.exists():
            self.logger.error(f"File {export_path} already exists! Overwriting file...")
        export_path.parent.mkdir(exist_ok=True, parents=True)
        await write_json(export_path, self.results)

    async def run(self,
                  methods: StringSequence,
                  endpoints: StringSequence,
                  data_list: OptionalDictSequence = None,
                  settings: OptionalDictSequence = None):
        await self.schedule_requests(methods, endpoints, data_list, settings)
        await self.export_results()
