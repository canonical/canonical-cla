import logging

from uvicorn.logging import DefaultFormatter


class CustomLogsFormatter(DefaultFormatter):
    def formatException(self, exc_info):
        """
        Format an exception so that it prints on a single line.
        """
        result = super().formatException(exc_info)
        return repr(result)  # Convert multi-line exception to single line

    def format(self, record):
        """
        Format the specified record as text.
        """
        result = super().format(record)
        if record.exc_info:
            # Replace newline chars in the exception message
            result = result.replace("\n", "\\n")
        return result


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
