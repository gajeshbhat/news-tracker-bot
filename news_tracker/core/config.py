"""
Configuration management for News Tracker Bot
Centralized configuration with validation and defaults
"""

import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Database configuration"""
    mongo_uri: str
    database_name: str = "news_db"
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        return cls(
            mongo_uri=os.getenv('MONGO_URI', 'mongodb://localhost:27017/news_db'),
            database_name=os.getenv('DB_NAME', 'news_db')
        )


@dataclass
class TelegramConfig:
    """Telegram bot configuration"""
    bot_token: str
    
    @classmethod
    def from_env(cls) -> 'TelegramConfig':
        token = os.getenv('SHABDA_TELE_KEY')
        if not token:
            raise ValueError("SHABDA_TELE_KEY environment variable is required")
        return cls(bot_token=token)


@dataclass
class NewsAPIConfig:
    """News API configuration"""
    api_key: str
    base_url: str = "https://newsapi.org/v2"
    sources_endpoint: str = "/sources"
    headlines_endpoint: str = "/top-headlines"
    
    @classmethod
    def from_env(cls) -> 'NewsAPIConfig':
        api_key = os.getenv('NEWS_API_KEY')
        if not api_key:
            raise ValueError("NEWS_API_KEY environment variable is required")
        return cls(api_key=api_key)


@dataclass
class TTSConfig:
    """Text-to-Speech configuration"""
    preferred_engine: str = "edge"  # edge, gtts, pyttsx3
    audio_output_dir: str = "data/audio"
    
    @classmethod
    def from_env(cls) -> 'TTSConfig':
        return cls(
            preferred_engine=os.getenv('TTS_ENGINE', 'edge'),
            audio_output_dir=os.getenv('AUDIO_DIR', 'data/audio')
        )


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    log_dir: str = "logs"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        return cls(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            log_dir=os.getenv('LOG_DIR', 'logs'),
            max_file_size=int(os.getenv('LOG_MAX_SIZE', str(10 * 1024 * 1024))),
            backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5'))
        )


@dataclass
class AppConfig:
    """Main application configuration"""
    database: DatabaseConfig
    telegram: TelegramConfig
    news_api: NewsAPIConfig
    tts: TTSConfig
    logging: LoggingConfig
    
    # Application settings
    refresh_interval_hours: int = 12
    max_summary_length: int = 4000  # Telegram message limit
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        return cls(
            database=DatabaseConfig.from_env(),
            telegram=TelegramConfig.from_env(),
            news_api=NewsAPIConfig.from_env(),
            tts=TTSConfig.from_env(),
            logging=LoggingConfig.from_env(),
            refresh_interval_hours=int(os.getenv('REFRESH_INTERVAL_HOURS', '12')),
            max_summary_length=int(os.getenv('MAX_SUMMARY_LENGTH', '4000'))
        )
    
    def validate(self) -> bool:
        """Validate configuration"""
        try:
            # Check required directories exist or can be created
            Path(self.tts.audio_output_dir).mkdir(parents=True, exist_ok=True)
            Path(self.logging.log_dir).mkdir(parents=True, exist_ok=True)
            
            # Validate TTS engine
            if self.tts.preferred_engine not in ['edge', 'gtts', 'pyttsx3']:
                raise ValueError(f"Invalid TTS engine: {self.tts.preferred_engine}")
            
            # Validate log level
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if self.logging.level.upper() not in valid_levels:
                raise ValueError(f"Invalid log level: {self.logging.level}")
            
            return True
            
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
        if not _config.validate():
            raise RuntimeError("Configuration validation failed")
    return _config


def reload_config() -> AppConfig:
    """Reload configuration from environment"""
    global _config
    _config = None
    return get_config()


# Convenience functions for common config access
def get_mongo_uri() -> str:
    return get_config().database.mongo_uri


def get_bot_token() -> str:
    return get_config().telegram.bot_token


def get_news_api_key() -> str:
    return get_config().news_api.api_key


def get_audio_dir() -> str:
    return get_config().tts.audio_output_dir


def get_tts_engine() -> str:
    return get_config().tts.preferred_engine
