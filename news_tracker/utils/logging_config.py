"""
Professional logging configuration for News Tracker Bot
Replaces the old logs.txt approach with proper Python logging
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    """
    Set up comprehensive logging for the News Tracker Bot
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
    
    Returns:
        Configured logger instance
    """
    
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger('news_tracker')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # Main application log (rotating)
    app_log_file = log_path / "news_tracker.log"
    app_handler = logging.handlers.RotatingFileHandler(
        app_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(detailed_formatter)
    logger.addHandler(app_handler)
    
    # Error log (separate file for errors only)
    error_log_file = log_path / "errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    # API calls log (for debugging API issues)
    api_log_file = log_path / "api_calls.log"
    api_handler = logging.handlers.RotatingFileHandler(
        api_log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=2
    )
    api_handler.setLevel(logging.DEBUG)
    api_handler.setFormatter(detailed_formatter)
    
    # Create API logger
    api_logger = logging.getLogger('news_tracker.api')
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.DEBUG)
    
    # Bot interactions log
    bot_log_file = log_path / "bot_interactions.log"
    bot_handler = logging.handlers.RotatingFileHandler(
        bot_log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=2
    )
    bot_handler.setLevel(logging.INFO)
    bot_handler.setFormatter(detailed_formatter)
    
    # Create bot logger
    bot_logger = logging.getLogger('news_tracker.bot')
    bot_logger.addHandler(bot_handler)
    bot_logger.setLevel(logging.INFO)
    
    logger.info("Logging system initialized")
    logger.info(f"Log files location: {log_path.absolute()}")
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance for a specific module"""
    if name:
        return logging.getLogger(f'news_tracker.{name}')
    return logging.getLogger('news_tracker')


# Convenience functions for different log types
def log_api_call(endpoint: str, status_code: int, response_time: float = None):
    """Log API call details"""
    logger = get_logger('api')
    message = f"API Call: {endpoint} | Status: {status_code}"
    if response_time:
        message += f" | Response Time: {response_time:.2f}s"
    logger.info(message)


def log_bot_interaction(user_id: int, command: str, success: bool = True):
    """Log bot user interactions"""
    logger = get_logger('bot')
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"User {user_id} | Command: {command} | Status: {status}")


def log_error_with_context(error: Exception, context: dict = None):
    """Log errors with additional context"""
    logger = get_logger()
    error_msg = f"Error: {str(error)}"
    if context:
        error_msg += f" | Context: {context}"
    logger.error(error_msg, exc_info=True)
