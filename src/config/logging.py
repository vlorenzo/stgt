"""Logging configuration for the application."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from flask import Flask
import coloredlogs

def configure_logging(app: Flask) -> None:
    """Configure logging for the application.
    
    Args:
        app: The Flask application instance.
    """
    # Set up basic configuration
    logging.basicConfig(level=logging.DEBUG)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s [in %(pathname)s:%(lineno)d]'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    )
    
    # Create and configure file handler (detailed logging)
    file_handler = RotatingFileHandler(
        'app.log',
        maxBytes=1024000,  # 1 MB   I need more space for the logs
        backupCount=10
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Create and configure console handler (main steps only)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = []  # Remove existing handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Install colored logs for console
    coloredlogs.install(
        level='INFO',
        logger=root_logger,
        fmt='%(asctime)s [%(levelname)s] %(message)s',
        level_styles={
            'debug': {'color': 'white'},
            'info': {'color': 'green'},
            'warning': {'color': 'yellow'},
            'error': {'color': 'red', 'bold': True},
            'critical': {'color': 'red', 'bold': True, 'background': 'white'}
        },
        field_styles={
            'asctime': {'color': 'white'},
            'levelname': {'color': 'white', 'bold': True}
        }
    )
    
    # Configure Flask logger
    app.logger.handlers = []  # Remove default Flask handlers
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    
    # Disable Werkzeug's default logger
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers = []
    werkzeug_logger.addHandler(file_handler)
    
    # Set OpenAI and httpx loggers to WARNING for console
    for logger_name in ['openai', 'httpx', 'httpcore']:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.addHandler(file_handler)  # Full debug in file
        console_handler_api = logging.StreamHandler(sys.stdout)
        console_handler_api.setFormatter(console_formatter)
        console_handler_api.setLevel(logging.WARNING)  # Only warnings and errors in console
        logger.addHandler(console_handler_api) 