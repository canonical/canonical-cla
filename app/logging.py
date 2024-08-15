import logging


def setup_logging():
    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"

    logger = logging.getLogger("uvicorn.access")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(log_format))
    logger.handlers = [handler]
    logging.basicConfig(level=logging.INFO, format=log_format)
