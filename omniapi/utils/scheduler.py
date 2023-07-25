import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler


class SchedulerManager:
    """
    SchedulerManager is a class for managing asynchronous scheduled tasks.

    Attributes:
        logger (logging.Logger): Logger instance for recording events related to the SchedulerManager.
        scheduler (AsyncIOScheduler): Scheduler instance for managing asynchronous jobs.
    """
    logger = logging.getLogger(__name__)

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def add_job(self, job, *args, **kwargs):
        """
        Add a job to the scheduler.

        Args:
            job (callable): The function to be executed by the scheduler.
        """
        self.scheduler.add_job(job, *args, **kwargs)

    def start(self):
        """
        Start the scheduler. The jobs added to the scheduler will start running at the specified intervals.
        """
        self.scheduler.start()
