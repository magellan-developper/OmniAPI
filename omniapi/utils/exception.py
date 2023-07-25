import logging

from typing import Optional


def raise_exception(message: str,
                    error_strategy: str,
                    exception_type: str = 'error',
                    logger: Optional[logging.Logger] = None):
    """Helper function to raise / log exceptions based on ERROR_HANDLING_STRATEGY in settings

    :param message: Exception Message
    :param error_strategy: Method to handle errors. Can be either 'log', 'raise', or 'ignore'.
    :param exception_type: Type of exception. Can be either 'error' or 'warning'
    :param logger: Logger of API Client
    """
    if error_strategy not in {'raise', 'log', 'ignore'}:
        raise RuntimeError("Error Handling Strategy in settings must be either 'raise', 'log', or 'ignore'!")
    if error_strategy == 'ignore':
        return False
    if exception_type not in {'error', 'warning'}:
        raise RuntimeError("Exception type must be either 'error' or 'warning'!")
    if error_strategy == 'log':
        if logger is None:
            raise RuntimeError("Logger must not be provided if logging exception")
        if exception_type == 'error':
            logger.error(message)
        else:
            logger.warning(message)
    if exception_type == 'error':
        raise RuntimeError(message)
    else:  # warning
        raise RuntimeWarning(message)
