import logging

from opentelemetry import trace
from pythonjsonlogger import jsonlogger

from app.config import config


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    service_name: str

    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)

        # Add trace and span IDs if they exist
        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            log_record["trace_id"] = format(span_context.trace_id, "032x")
            log_record["span_id"] = format(span_context.span_id, "016x")
            log_record["trace_flags"] = format(span_context.trace_flags, "02x")

        # Add service name
        if not log_record.get("service"):
            self.service_name = trace.get_tracer_provider().resource.attributes.get(
                "service.name", "unknown"
            )

        log_record["service"] = self.service_name
        log_record["severity"] = record.levelname
        log_record["timestamp"] = self.formatTime(record)


def configure_logger():
    """Configure the root logger with JSON formatting and trace context"""
    logger = logging.getLogger()
    if config.debug_mode:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create a handler that outputs to stdout
    handler = logging.StreamHandler()

    # Create different formatters based on debug mode
    if config.debug_mode:
        # User-friendly format for development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        # JSON format for production
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(service)s %(severity)s %(name)s %(message)s"
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Configure FastAPI and Uvicorn loggers to use the same configuration
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        logger = logging.getLogger(logger_name)
        logger.handlers = []  # Remove default handlers
        logger.propagate = True  # Propagate to root logger with our custom formatter

    return logger
