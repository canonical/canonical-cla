import logging
from types import TracebackType

from uvicorn.logging import DefaultFormatter


class CustomLogsFormatter(DefaultFormatter):
    def format(self, record):
        formatted = super().format(record)
        return formatted.replace("\n", "\\n")


def setup_logging():
    log_format = "%(asctime)s [%(levelname)s] (%(name)s:%(module)s) %(message)s"
    handler = logging.StreamHandler()
    handler.setFormatter(CustomLogsFormatter(fmt=log_format))

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]

    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers = [handler]

    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers = [handler]

    logging.basicConfig(level=logging.INFO, format=log_format, handlers=[handler])
