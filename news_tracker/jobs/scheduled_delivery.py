"""
Scheduled Delivery Job Handler

Manages automated news delivery based on user schedules.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import pytz
from telegram import Bot
from telegram.ext import JobQueue
from langdetect import detect, LangDetectException

from news_tracker.core.config import get_config, AppConfig
from news_tracker.core.schedule_manager import ScheduleManager, Schedule
from news_tracker.core.product_keys import ProductKeyManager
from news_tracker.api.news_client import NewsService
from news_tracker.api.tts_engines import TTSManager


class ScheduledDelivery:
    """Handles scheduled news delivery"""
    
    def __init__(self, config: AppConfig, job_queue: JobQueue):
        """
        Initialize scheduled delivery handler
        
        Args:
            config: Bot configuration
            job_queue: Telegram job queue
        """
        self.config = config
        self.job_queue = job_queue
        self.schedule_manager = ScheduleManager(config.database.mongo_uri)
        self.key_manager = ProductKeyManager(config.database.mongo_uri)
        self.news_service = NewsService()
        self.tts_manager = TTSManager()
        self.logger = logging.getLogger(__name__)

        # Track active jobs (schedule_id -> Job)
        self.active_jobs = {}
    
    def initialize_all_schedules(self):
        """
        Initialize jobs for all active schedules
        Called on bot startup
        """
        try:
            schedules = self.schedule_manager.get_active_schedules()
            self.logger.info(f"Initializing {len(schedules)} active schedules")
            
            for schedule in schedules:
                self.schedule_job(schedule)
            
            self.logger.info(f"Initialized {len(self.active_jobs)} schedule jobs")
            
        except Exception as e:
            self.logger.error(f"Error initializing schedules: {e}")
    
    def schedule_job(self, schedule: Schedule):
        """
        Schedule a job for a specific schedule
        
        Args:
            schedule: Schedule object
        """
        try:
            # Remove existing job if any
            if schedule.schedule_id in self.active_jobs:
                self.active_jobs[schedule.schedule_id].schedule_removal()
                del self.active_jobs[schedule.schedule_id]
            
            # Calculate when to run
            if not schedule.next_send:
                self.logger.warning(f"Schedule {schedule.schedule_id} has no next_send time")
                return
            
            # Calculate seconds until next send
            now = datetime.utcnow()
            if schedule.next_send <= now:
                # If overdue, schedule for immediate delivery
                when = 1  # 1 second from now
            else:
                when = (schedule.next_send - now).total_seconds()
            
            # Create job
            job = self.job_queue.run_once(
                self._deliver_news,
                when=when,
                data={'schedule_id': schedule.schedule_id},
                name=f"schedule_{schedule.schedule_id}"
            )
            
            self.active_jobs[schedule.schedule_id] = job
            
            self.logger.info(
                f"Scheduled job for {schedule.schedule_id} "
                f"to run in {when:.0f} seconds (at {schedule.next_send})"
            )
            
        except Exception as e:
            self.logger.error(f"Error scheduling job for {schedule.schedule_id}: {e}")
    
    async def _deliver_news(self, context):
        """
        Deliver news for a schedule (job callback)
        
        Args:
            context: Telegram job context
        """
        schedule_id = context.job.data['schedule_id']
        
        try:
            # Get schedule
            schedule = self.schedule_manager.get_schedule_by_id(schedule_id)
            
            if not schedule:
                self.logger.warning(f"Schedule {schedule_id} not found")
                return
            
            if not schedule.is_active:
                self.logger.info(f"Schedule {schedule_id} is inactive, skipping")
                return
            
            # Check user's product key and rate limits
            if not await self._check_rate_limit(schedule.user_id, context.bot):
                return
            
            # Fetch and deliver news
            await self._fetch_and_send_news(schedule, context.bot)
            
            # Mark as sent and calculate next send time
            self.schedule_manager.mark_as_sent(schedule_id)
            
            # Reschedule for next delivery
            updated_schedule = self.schedule_manager.get_schedule_by_id(schedule_id)
            if updated_schedule and updated_schedule.is_active:
                self.schedule_job(updated_schedule)
            
        except Exception as e:
            self.logger.error(f"Error delivering news for schedule {schedule_id}: {e}")
            
            # Try to reschedule anyway
            try:
                schedule = self.schedule_manager.get_schedule_by_id(schedule_id)
                if schedule and schedule.is_active:
                    # Schedule for retry in 1 hour
                    schedule.next_send = datetime.utcnow() + timedelta(hours=1)
                    self.schedule_job(schedule)
            except Exception as retry_error:
                self.logger.error(f"Error rescheduling after failure: {retry_error}")
    
    async def _check_rate_limit(self, user_id: int, bot: Bot) -> bool:
        """
        Check if user has exceeded their daily rate limit

        Args:
            user_id: Telegram user ID
            bot: Telegram bot instance

        Returns:
            True if within limit, False if exceeded
        """
        try:
            # Get user's product key
            key = self.key_manager.get_key_by_user_id(user_id)

            if not key:
                self.logger.warning(f"No product key found for user {user_id}")
                await bot.send_message(
                    chat_id=user_id,
                    text="❌ Your product key is no longer valid. Please contact the administrator."
                )
                return False

            if not key.is_active:
                self.logger.warning(f"Product key for user {user_id} is inactive")
                await bot.send_message(
                    chat_id=user_id,
                    text="❌ Your product key has been deactivated. Please contact the administrator."
                )
                return False

            # TODO: Implement actual rate limiting with request counting
            # For now, just check if key is valid and active
            # Future: Track daily request count in MongoDB and compare with max_requests_per_day

            return True

        except Exception as e:
            self.logger.error(f"Error checking rate limit: {e}")
            return False
    
    async def _fetch_and_send_news(self, schedule: Schedule, bot: Bot):
        """
        Fetch news and send to user

        Args:
            schedule: Schedule object
            bot: Telegram bot instance
        """
        try:
            # Fetch news for each source
            all_articles = []
            source_info = {}  # Map source_id to source metadata

            for source_id in schedule.sources:
                try:
                    # Get source info from database
                    source = self.news_service.database.get_source_by_id(source_id)
                    if not source:
                        self.logger.warning(f"Source {source_id} not found in database")
                        continue

                    source_name = source.get('name', source_id)
                    source_language = source.get('language', 'en')

                    # Store source metadata
                    source_info[source_id] = {
                        'name': source_name,
                        'language': source_language
                    }

                    # Fetch and store articles
                    self.news_service.fetch_and_store_articles(source_name)

                    # Get articles from database
                    articles_doc = self.news_service.database.get_articles_by_source(source_id)
                    if articles_doc and 'articles' in articles_doc:
                        articles = articles_doc['articles'][:5]  # Max 5 per source
                        all_articles.extend(articles)

                except Exception as e:
                    self.logger.error(f"Error fetching news from {source_id}: {e}")

            if not all_articles:
                # Send notification that no articles available
                await bot.send_message(
                    chat_id=schedule.user_id,
                    text=(
                        "📰 *Scheduled News Delivery*\n\n"
                        "No new articles available from your selected sources at this time.\n\n"
                        "We'll try again at the next scheduled time."
                    ),
                    parse_mode='Markdown'
                )
                return

            # Send based on format preference
            if schedule.format in ['text', 'both']:
                await self._send_text_summary(schedule, all_articles, source_info, bot)

            if schedule.format in ['audio', 'both']:
                await self._send_audio_summary(schedule, all_articles, source_info, bot)

        except Exception as e:
            self.logger.error(f"Error fetching and sending news: {e}")
            raise
    
    def _strip_html(self, text: str) -> str:
        """Remove HTML tags and clean up text"""
        if not text:
            return ""

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Decode common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language of text using langdetect"""
        if not text or len(text.strip()) < 10:
            return None

        try:
            # Detect language (returns ISO 639-1 code like 'en', 'es', etc.)
            detected = detect(text)
            return detected
        except LangDetectException:
            return None

    def _get_language_name(self, lang_code: str) -> str:
        """Get human-readable language name from code"""
        lang_names = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'ru': 'Russian',
            'nl': 'Dutch',
            'sv': 'Swedish',
            'no': 'Norwegian',
            'da': 'Danish',
            'fi': 'Finnish',
            'pl': 'Polish',
            'tr': 'Turkish',
            'he': 'Hebrew'
        }
        return lang_names.get(lang_code, lang_code.upper())

    def _is_valid_article(self, article: dict, source_name: str, expected_language: str = 'en') -> bool:
        """
        Check if article has meaningful content and matches expected language

        Args:
            article: Article dictionary
            source_name: Name of the news source
            expected_language: Expected language code (e.g., 'en', 'es')

        Returns:
            bool: True if article is valid and in expected language
        """
        title = article.get('title', '')
        description = article.get('description', '')

        # Filter out generic "Google News" titles
        if title.strip().lower() == 'google news':
            return False

        # Filter out descriptions that are just generic Google News text
        if description and 'comprehensive up-to-date news coverage' in description.lower():
            return False

        # Filter out descriptions that are just "aggregated from sources all over the world"
        if description and 'aggregated from sources all over the world' in description.lower():
            return False

        # Check language if we have enough text
        text_to_check = f"{title} {description}".strip()
        if len(text_to_check) > 20:
            detected_lang = self._detect_language(text_to_check)
            if detected_lang and detected_lang != expected_language:
                self.logger.debug(
                    f"Filtering article from {source_name}: "
                    f"expected {expected_language}, got {detected_lang} - '{title[:50]}...'"
                )
                return False

        return True

    async def _send_text_summary(self, schedule: Schedule, articles: list, source_info: Dict, bot: Bot):
        """Send text summary of articles"""
        try:
            # Group by source
            sources_text = {}
            for article in articles:
                source = article.get('source', {}).get('name', 'Unknown')
                if source not in sources_text:
                    sources_text[source] = []
                sources_text[source].append(article)

            # Build message
            message = "📰 *Your Scheduled News Delivery*\n\n"
            language_warnings = []

            for source, source_articles in sources_text.items():
                # Get expected language for this source
                source_id = source_articles[0].get('source', {}).get('id', '')
                expected_lang = source_info.get(source_id, {}).get('language', 'en')

                message += f"*{source}*\n"

                # Filter and process articles
                valid_articles = 0
                filtered_count = 0

                for article in source_articles:
                    # Skip invalid/generic articles (with language check)
                    if not self._is_valid_article(article, source, expected_lang):
                        filtered_count += 1
                        continue

                    if valid_articles >= 5:  # Max 5 per source
                        break

                    title = article.get('title', 'No title')
                    description = article.get('description', '')
                    url = article.get('url', '')

                    # Clean HTML from title and description
                    title = self._strip_html(title)
                    description = self._strip_html(description)

                    # Add title with link
                    if url:
                        message += f"• [{title}]({url})\n"
                    else:
                        message += f"• {title}\n"

                    # Add description if available (truncate if too long)
                    if description:
                        # Truncate description to ~150 chars
                        if len(description) > 150:
                            description = description[:147] + "..."
                        message += f"  _{description}_\n"

                    message += "\n"
                    valid_articles += 1

                # Notify if articles were filtered due to language mismatch
                if filtered_count > 0 and valid_articles == 0:
                    lang_name = self._get_language_name(expected_lang)
                    language_warnings.append(
                        f"⚠️ *{source}*: All articles were in a different language. "
                        f"This source is configured for {lang_name}."
                    )
                elif filtered_count > 0:
                    message += f"  _({filtered_count} article(s) filtered due to language mismatch)_\n\n"

                # Add spacing between sources
                if valid_articles > 0:
                    message += "\n"

            # Add language warnings at the end
            if language_warnings:
                message += "\n" + "\n".join(language_warnings) + "\n\n"

            message += f"_Delivered at {schedule.time} {schedule.timezone}_"

            await bot.send_message(
                chat_id=schedule.user_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )

        except Exception as e:
            self.logger.error(f"Error sending text summary: {e}")
            raise
    
    async def _send_audio_summary(self, schedule: Schedule, articles: list, source_info: Dict, bot: Bot):
        """Send audio summary of articles"""
        try:
            # Determine primary language (use first source's language)
            primary_language = 'en'
            if source_info:
                first_source_id = list(source_info.keys())[0]
                primary_language = source_info[first_source_id].get('language', 'en')

            # Generate summary text
            source_names = [info['name'] for info in source_info.values()]
            sources_str = " and ".join(source_names) if source_names else "your selected sources"
            summary_text = f"Here are your scheduled news headlines from {sources_str}. "

            # Group articles by source for better organization
            articles_by_source = {}
            for article in articles:
                source = article.get('source', {}).get('name', 'Unknown')
                if source not in articles_by_source:
                    articles_by_source[source] = []
                articles_by_source[source].append(article)

            # Read headlines and descriptions for each source
            for source, source_articles in articles_by_source.items():
                # Get expected language for this source
                source_id = source_articles[0].get('source', {}).get('id', '')
                expected_lang = source_info.get(source_id, {}).get('language', 'en')

                # Filter valid articles first (with language check)
                valid_articles = [
                    a for a in source_articles
                    if self._is_valid_article(a, source, expected_lang)
                ]

                if not valid_articles:
                    continue

                summary_text += f"From {source}. "

                for article in valid_articles[:5]:  # Max 5 per source for audio
                    title = article.get('title', '')
                    description = article.get('description', '')

                    # Clean HTML from title and description
                    title = self._strip_html(title)
                    description = self._strip_html(description)

                    if title:
                        summary_text += f"{title}. "
                        # Add description if available and not too long
                        if description and len(description) < 200:
                            summary_text += f"{description}. "
                        summary_text += "In other news, "

            # Remove trailing "In other news, " before the closing
            if summary_text.endswith("In other news, "):
                summary_text = summary_text[:-len("In other news, ")]

            summary_text += "That's all for now. Check back later for more updates."

            # Generate audio file
            import tempfile
            import os
            audio_path = os.path.join(
                tempfile.gettempdir(),
                f"schedule_{schedule.schedule_id}_{datetime.utcnow().timestamp()}.mp3"
            )

            # Use TTS manager to generate audio (async version) with detected language
            self.logger.info(f"Generating audio in language: {primary_language}")

            if await self.tts_manager.generate_audio_async(
                summary_text,
                primary_language,  # Use detected language from sources
                audio_path,
                self.config.tts.preferred_engine
            ):
                lang_name = self._get_language_name(primary_language)
                with open(audio_path, 'rb') as audio:
                    await bot.send_audio(
                        chat_id=schedule.user_id,
                        audio=audio,
                        title=f"Scheduled News Summary ({lang_name})",
                        caption=f"🔊 Audio summary delivered at {schedule.time} {schedule.timezone}"
                    )

                # Clean up temp file
                try:
                    os.remove(audio_path)
                except:
                    pass
            else:
                self.logger.error(f"Failed to generate audio file in language: {primary_language}")

        except Exception as e:
            self.logger.error(f"Error sending audio summary: {e}")
            # Don't raise - text was already sent if format is 'both'
    
    def cancel_schedule(self, schedule_id: str):
        """
        Cancel a scheduled job
        
        Args:
            schedule_id: Schedule ID
        """
        try:
            if schedule_id in self.active_jobs:
                self.active_jobs[schedule_id].schedule_removal()
                del self.active_jobs[schedule_id]
                self.logger.info(f"Cancelled job for schedule {schedule_id}")
            
        except Exception as e:
            self.logger.error(f"Error cancelling schedule {schedule_id}: {e}")
    
    def get_active_job_count(self) -> int:
        """Get number of active scheduled jobs"""
        return len(self.active_jobs)

