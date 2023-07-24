import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler


class SchedulerManager:
    logger = logging.getLogger(__name__)

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def add_job(self, job, interval):
        self.scheduler.add_job(job, interval)

    def start(self):
        self.scheduler.start()
