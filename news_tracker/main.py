"""
Main entry point for News Tracker Bot
Modernized application with proper structure and error handling
"""

import asyncio
import signal
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file before anything else
load_dotenv()

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from .core.config import get_config
from .utils.logging_config import setup_logging, get_logger
from .bot.handlers import NewsTrackerBot
from .bot.schedule_handlers import ScheduleHandlers
from .api.news_client import NewsService
from .jobs.scheduled_delivery import ScheduledDelivery


class NewsTrackerApplication:
    """Main application class"""
    
    def __init__(self):
        # Load configuration
        self.config = get_config()
        
        # Setup logging
        setup_logging(
            log_level=self.config.logging.level,
            log_dir=self.config.logging.log_dir
        )
        
        self.logger = get_logger('main')
        self.logger.info("Starting News Tracker Bot v2.0")
        
        # Initialize services
        self.news_service = NewsService()
        self.bot_handlers = NewsTrackerBot()
        self.schedule_handlers = None  # Initialized after application is created
        self.scheduled_delivery = None  # Initialized after application is created

        # Telegram application
        self.application = None
        
    def setup_telegram_bot(self):
        """Setup Telegram bot with handlers"""
        self.logger.info("Setting up Telegram bot...")
        
        # Create application
        self.application = Application.builder().token(self.config.telegram.bot_token).build()

        # Initialize schedule handlers (needs application for job queue)
        self.schedule_handlers = ScheduleHandlers(self.config)
        self.scheduled_delivery = ScheduledDelivery(self.config, self.application.job_queue)

        # Add command handlers
        self.application.add_handler(CommandHandler('start', self.bot_handlers.start_command))
        self.application.add_handler(CommandHandler('register', self.bot_handlers.register_command))
        self.application.add_handler(CommandHandler('help', self.bot_handlers.help_command))
        self.application.add_handler(CommandHandler('latest', self.bot_handlers.latest_command))

        # Add schedule conversation handler
        self.application.add_handler(self.schedule_handlers.get_conversation_handler())

        # Add callback query handlers for /latest pagination and format selection
        self.application.add_handler(CallbackQueryHandler(
            self.bot_handlers.handle_latest_callback,
            pattern='^latest_'
        ))
        self.application.add_handler(CallbackQueryHandler(
            self.bot_handlers.handle_format_callback,
            pattern='^format_'
        ))

        # Add message handler for text messages (must be last)
        self.application.add_handler(MessageHandler(filters.TEXT, self.bot_handlers.handle_message))
        
        # Setup job queue for periodic tasks
        if self.application.job_queue:
            # Periodic news refresh (every 12 hours)
            self.application.job_queue.run_repeating(
                self._periodic_refresh,
                interval=self.config.refresh_interval_hours * 3600,
                first=self.config.refresh_interval_hours * 3600
            )
            
            # Session cleanup (every 10 minutes)
            self.application.job_queue.run_repeating(
                self._cleanup_sessions,
                interval=600,  # 10 minutes
                first=600
            )
            
            self.logger.info("Job queue configured")
        else:
            self.logger.warning("Job queue not available")
    
    async def _periodic_refresh(self, context):
        """Periodic task to refresh news sources"""
        try:
            self.logger.info("Running periodic news refresh...")
            success = self.news_service.initialize_sources()
            if success:
                self.logger.info("Periodic news refresh completed successfully")
            else:
                self.logger.error("Periodic news refresh failed")
        except Exception as e:
            self.logger.error(f"Error in periodic refresh: {e}")
    
    async def _cleanup_sessions(self, context):
        """Periodic task to cleanup expired sessions"""
        try:
            self.bot_handlers.session_manager.cleanup_expired_sessions()
        except Exception as e:
            self.logger.error(f"Error in session cleanup: {e}")
    
    def initialize_database(self) -> bool:
        """Initialize database with news sources"""
        self.logger.info("Initializing database...")
        
        try:
            success = self.news_service.initialize_sources()
            if success:
                self.logger.info("Database initialization completed")
                return True
            else:
                self.logger.error("Database initialization failed")
                return False
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")
            return False
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            if self.application and self.application.running:
                self.application.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start(self):
        """Start the bot application (synchronous)"""
        try:
            self.logger.info("Starting News Tracker Bot...")

            # Setup signal handlers
            self.setup_signal_handlers()

            # Setup Telegram bot
            self.setup_telegram_bot()

            # Initialize database if needed
            sources = self.news_service.database.get_all_sources()
            if not sources:
                self.logger.info("No sources found, initializing database...")
                if not self.initialize_database():
                    self.logger.error("Failed to initialize database, exiting...")
                    return False
            else:
                self.logger.info(f"Found {len(sources)} news sources in database")

            # Initialize scheduled jobs
            self.logger.info("Initializing scheduled news deliveries...")
            self.scheduled_delivery.initialize_all_schedules()
            active_jobs = self.scheduled_delivery.get_active_job_count()
            self.logger.info(f"Initialized {active_jobs} scheduled delivery jobs")

            # Start the bot
            self.logger.info("Bot is ready! Starting polling...")
            self.application.run_polling(drop_pending_updates=True)

        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            return False

        return True
    
    def stop(self):
        """Stop the bot application"""
        self.logger.info("Stopping News Tracker Bot...")

        if self.application and self.application.running:
            self.application.stop()

        self.logger.info("Bot stopped")


def main():
    """Main entry point"""
    app = NewsTrackerApplication()

    try:
        return app.start()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        return 0
    except Exception as e:
        print(f"Application error: {e}")
        return 1
    finally:
        app.stop()


def run():
    """Entry point for scripts"""
    try:
        return main()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        return 0
    except Exception as e:
        print(f"Application error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run())
