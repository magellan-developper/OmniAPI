from omniapi.clients.base import BaseClient
from omniapi.utils.result import Result


class JsonClient(BaseClient):
    async def request_callback(self, result: Result, url: str, data: dict, setup_info):
        pass



    async def export_results(self, results):
        export_path = self.config.export_results_path
        if export_path is None:
            return
        export_path = Path(self.config.export_results_path)
        if export_path.exists():
            self.logger.error(f"File {export_path} already exists! Overwriting file...")

        export_path.parent.mkdir(exist_ok=True, parents=True)
        await self.write_json(self.config.export_results_path, results)