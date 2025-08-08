import logging
import sys

def setup_logging(service_name: str, log_level: int = logging.INFO):
    """
    Configures logging for a microservice to output to the console.

    File handling is managed by the service that launches the process.

    :param service_name: The name of the service, used for the logger name.
    :param log_level: The logging level (e.g., logging.INFO).
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(log_level)
    logger.propagate = False

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Add handler to the logger, but only if it hasn't been added before
    if not logger.handlers:
        logger.addHandler(console_handler)

    return logger
