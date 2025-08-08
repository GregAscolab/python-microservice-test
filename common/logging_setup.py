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
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Get the root logger for the service
    logger = logging.getLogger(service_name)
    logger.setLevel(log_level)

    # Prevent logs from being propagated to the root logger if it has handlers
    logger.propagate = False

    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create a file handler
    file_handler = logging.FileHandler(f"logs/{service_name}.log", mode='w')
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
