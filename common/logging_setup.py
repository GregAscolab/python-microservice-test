import logging
import os
import sys

def setup_logging(service_name: str, log_level: int = logging.INFO):
    """
    Configures logging for a microservice.

    This sets up a logger that writes to both a file in the `logs/` directory
    and to the console.

    :param service_name: The name of the service, used for the log file name.
    :param log_level: The logging level (e.g., logging.INFO).
    """
    # Use an absolute path for the logs directory to be safe
    log_dir = os.path.abspath("logs")
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(service_name)
    logger.setLevel(log_level)
    logger.propagate = False

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create a file handler
    file_handler = logging.FileHandler(os.path.join(log_dir, f"{service_name}.log"), mode='w')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Create a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger, but only if they haven't been added before
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
