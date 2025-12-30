#!/usr/bin/env python3
"""
Cleanup script for News Tracker Bot
Handles cleanup of old audio files, logs, and database data
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple
from dotenv import load_dotenv

# Load .env file before anything else
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from news_tracker.core.config import get_config
from news_tracker.api.news_client import NewsDatabase


class CleanupManager:
    """Manages cleanup of temporary files and old data"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = logging.getLogger('cleanup')
        self.database = NewsDatabase()
        
    def cleanup_audio_files(self, max_age_hours: int = 24) -> Tuple[int, int]:
        """
        Clean up audio files older than specified hours
        
        Args:
            max_age_hours: Maximum age of audio files in hours (default: 24)
            
        Returns:
            Tuple of (files_deleted, bytes_freed)
        """
        audio_dir = Path(self.config.tts.audio_output_dir)
        
        if not audio_dir.exists():
            self.logger.info(f"Audio directory {audio_dir} does not exist")
            return 0, 0
        
        cutoff_time = time.time() - (max_age_hours * 3600)
        files_deleted = 0
        bytes_freed = 0
        
        for audio_file in audio_dir.glob('*.mp3'):
            try:
                # Skip .keep files
                if audio_file.name == '.keep':
                    continue
                    
                file_stat = audio_file.stat()
                
                # Check if file is older than cutoff
                if file_stat.st_mtime < cutoff_time:
                    file_size = file_stat.st_size
                    audio_file.unlink()
                    files_deleted += 1
                    bytes_freed += file_size
                    self.logger.debug(f"Deleted old audio file: {audio_file.name}")
                    
            except Exception as e:
                self.logger.error(f"Error deleting {audio_file}: {e}")
        
        if files_deleted > 0:
            self.logger.info(
                f"Cleaned up {files_deleted} audio files, "
                f"freed {bytes_freed / 1024 / 1024:.2f} MB"
            )
        
        return files_deleted, bytes_freed
    
    def cleanup_old_articles(self, max_age_days: int = 7) -> int:
        """
        Clean up articles older than specified days
        
        Args:
            max_age_days: Maximum age of articles in days (default: 7)
            
        Returns:
            Number of article collections deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            
            # Get all article collections
            collections = self.database.db.list_collection_names()
            article_collections = [c for c in collections if c.startswith('articles_')]
            
            deleted_count = 0
            
            for collection_name in article_collections:
                collection = self.database.db[collection_name]
                
                # Check the last_updated field
                latest_doc = collection.find_one(sort=[('last_updated', -1)])
                
                if latest_doc and 'last_updated' in latest_doc:
                    if latest_doc['last_updated'] < cutoff_date:
                        # Delete the entire collection
                        collection.drop()
                        deleted_count += 1
                        self.logger.info(f"Deleted old article collection: {collection_name}")
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old article collections")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old articles: {e}")
            return 0
    
    def cleanup_inactive_schedules(self, max_age_days: int = 90) -> int:
        """
        Clean up inactive schedules older than specified days
        
        Args:
            max_age_days: Maximum age of inactive schedules in days (default: 90)
            
        Returns:
            Number of schedules deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            
            result = self.database.db.schedules.delete_many({
                'is_active': False,
                'updated_at': {'$lt': cutoff_date}
            })
            
            deleted_count = result.deleted_count
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} inactive schedules")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up inactive schedules: {e}")
            return 0
    
    def get_storage_stats(self) -> dict:
        """Get storage statistics for audio files and logs"""
        stats = {
            'audio': {'count': 0, 'size_mb': 0},
            'logs': {'count': 0, 'size_mb': 0}
        }
        
        # Audio files
        audio_dir = Path(self.config.tts.audio_output_dir)
        if audio_dir.exists():
            for audio_file in audio_dir.glob('*.mp3'):
                if audio_file.name != '.keep':
                    stats['audio']['count'] += 1
                    stats['audio']['size_mb'] += audio_file.stat().st_size / 1024 / 1024
        
        # Log files
        log_dir = Path(self.config.logging.log_dir)
        if log_dir.exists():
            for log_file in log_dir.glob('*.log*'):
                if log_file.name != '.keep':
                    stats['logs']['count'] += 1
                    stats['logs']['size_mb'] += log_file.stat().st_size / 1024 / 1024
        
        return stats
    
    def run_full_cleanup(
        self,
        audio_max_age_hours: int = 24,
        articles_max_age_days: int = 7,
        schedules_max_age_days: int = 90
    ) -> dict:
        """
        Run full cleanup of all temporary data
        
        Args:
            audio_max_age_hours: Max age for audio files in hours
            articles_max_age_days: Max age for articles in days
            schedules_max_age_days: Max age for inactive schedules in days
            
        Returns:
            Dictionary with cleanup results
        """
        self.logger.info("Starting full cleanup...")
        
        # Get stats before cleanup
        stats_before = self.get_storage_stats()
        
        # Run cleanups
        audio_deleted, audio_bytes = self.cleanup_audio_files(audio_max_age_hours)
        articles_deleted = self.cleanup_old_articles(articles_max_age_days)
        schedules_deleted = self.cleanup_inactive_schedules(schedules_max_age_days)
        
        # Get stats after cleanup
        stats_after = self.get_storage_stats()
        
        results = {
            'audio_files_deleted': audio_deleted,
            'audio_mb_freed': audio_bytes / 1024 / 1024,
            'article_collections_deleted': articles_deleted,
            'inactive_schedules_deleted': schedules_deleted,
            'storage_before': stats_before,
            'storage_after': stats_after
        }
        
        self.logger.info("Cleanup completed")
        self.logger.info(f"Results: {results}")
        
        return results


def main():
    """Main entry point for cleanup script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='News Tracker Bot Cleanup')
    parser.add_argument(
        '--audio-age',
        type=int,
        default=24,
        help='Maximum age of audio files in hours (default: 24)'
    )
    parser.add_argument(
        '--articles-age',
        type=int,
        default=7,
        help='Maximum age of articles in days (default: 7)'
    )
    parser.add_argument(
        '--schedules-age',
        type=int,
        default=90,
        help='Maximum age of inactive schedules in days (default: 90)'
    )
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Only show storage statistics without cleaning'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    cleanup_manager = CleanupManager()
    
    if args.stats_only:
        stats = cleanup_manager.get_storage_stats()
        print("\n📊 Storage Statistics:")
        print(f"  Audio Files: {stats['audio']['count']} files, {stats['audio']['size_mb']:.2f} MB")
        print(f"  Log Files: {stats['logs']['count']} files, {stats['logs']['size_mb']:.2f} MB")
        print()
    else:
        results = cleanup_manager.run_full_cleanup(
            audio_max_age_hours=args.audio_age,
            articles_max_age_days=args.articles_age,
            schedules_max_age_days=args.schedules_age
        )
        
        print("\n✅ Cleanup Results:")
        print(f"  Audio files deleted: {results['audio_files_deleted']} ({results['audio_mb_freed']:.2f} MB freed)")
        print(f"  Article collections deleted: {results['article_collections_deleted']}")
        print(f"  Inactive schedules deleted: {results['inactive_schedules_deleted']}")
        print()


if __name__ == '__main__':
    main()

