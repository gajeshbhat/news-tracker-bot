"""
Database setup script for News Tracker Bot
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from news_tracker.core.config import get_config
from news_tracker.utils.logging_config import setup_logging, get_logger
from news_tracker.api.news_client import NewsService


def main():
    """Initialize the database with news sources"""
    try:
        # Setup basic logging
        setup_logging(log_level="INFO")
        logger = get_logger('setup')
        
        logger.info("🗄️ Initializing News Tracker Bot database...")
        
        # Initialize news service
        news_service = NewsService()
        
        # Initialize sources
        success = news_service.initialize_sources()
        
        if success:
            # Get source count
            sources = news_service.database.get_all_sources()
            logger.info(f"✅ Database initialization completed successfully!")
            logger.info(f"📰 Loaded {len(sources)} news sources")
            print(f"\n🎉 Setup completed! Found {len(sources)} news sources.")
            return 0
        else:
            logger.error("❌ Database initialization failed")
            print("\n❌ Setup failed. Check logs for details.")
            return 1
            
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
