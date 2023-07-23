import logging

from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler


class SchedulerManager:
    logger = logging.getLogger(__name__)

    def __init__(self):
        executors = {
            'default': {'type': 'asyncio'},
            'processpool': ProcessPoolExecutor(max_workers=MAX_BACKGROUND_WORKERS)
        }
        self.scheduler = AsyncIOScheduler(executors=executors)

    def add_async_job(self, job, interval):
        self.scheduler.add_job(job, interval)

    def add_sync_job(self, job, interval):
        self.scheduler.add_job(job, interval, executor='processpool')

    def start(self):
        self.scheduler.start()
