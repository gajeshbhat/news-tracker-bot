"""
News API client for fetching news data
Modernized version with proper error handling and logging
"""

import re
import requests
import time
import feedparser
from typing import Dict, List, Optional, Any
from pymongo import MongoClient
from gtts import lang
from langdetect import detect, LangDetectException

from ..core.config import get_config
from ..utils.logging_config import get_logger, log_api_call, log_error_with_context
from .tts_engines import TTSManager


class NewsAPIClient:
    """Client for interacting with News API"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger('api')
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.config.news_api.api_key,
            'User-Agent': 'NewsTrackerBot/2.0'
        })
    
    def get_sources(self) -> Optional[Dict[str, Any]]:
        """Fetch available news sources"""
        url = f"{self.config.news_api.base_url}{self.config.news_api.sources_endpoint}"
        
        try:
            start_time = time.time()
            response = self.session.get(url, timeout=30)
            response_time = time.time() - start_time
            
            log_api_call(url, response.status_code, response_time)
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Fetched {len(data.get('sources', []))} news sources")
                return data
            else:
                self.logger.error(f"API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            log_error_with_context(e, {'endpoint': url, 'method': 'get_sources'})
            return None
    
    def get_headlines(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Fetch headlines for a specific source"""
        url = f"{self.config.news_api.base_url}{self.config.news_api.headlines_endpoint}"
        params = {'sources': source_id}
        
        try:
            start_time = time.time()
            response = self.session.get(url, params=params, timeout=30)
            response_time = time.time() - start_time
            
            log_api_call(f"{url}?sources={source_id}", response.status_code, response_time)
            
            if response.status_code == 200:
                data = response.json()
                article_count = len(data.get('articles', []))
                self.logger.info(f"Fetched {article_count} articles for {source_id}")
                return data
            else:
                self.logger.error(f"API error for {source_id}: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            log_error_with_context(e, {'endpoint': url, 'source_id': source_id})
            return None


class NewsDatabase:
    """Database operations for news data"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger('database')
        
        try:
            self.client = MongoClient(
                self.config.database.mongo_uri,
                serverSelectionTimeoutMS=5000
            )
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.config.database.database_name]
            self.logger.info("Database connection established")
        except Exception as e:
            log_error_with_context(e, {'mongo_uri': self.config.database.mongo_uri})
            raise
    
    def save_sources(self, sources: List[Dict[str, Any]]) -> bool:
        """Save news sources to database"""
        try:
            # Clear existing sources
            self.db.news_sources.delete_many({})
            
            # Insert new sources
            for source in sources:
                source_doc = {
                    "search_id": source['id'],
                    "name": source['name'],
                    "description": source['description'],
                    "url": source['url'],
                    "category": source['category'],
                    "language": source['language'],
                    "country": source['country'],
                    "api_url": f"https://newsapi.org/v2/top-headlines?sources={source['id']}"
                }
                self.db.news_sources.insert_one(source_doc)
            
            self.logger.info(f"Saved {len(sources)} news sources to database")
            return True
            
        except Exception as e:
            log_error_with_context(e, {'operation': 'save_sources', 'count': len(sources)})
            return False
    
    def get_source_by_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get source by search_id"""
        try:
            return self.db.news_sources.find_one({"search_id": source_id})
        except Exception as e:
            log_error_with_context(e, {'operation': 'get_source_by_id', 'source_id': source_id})
            return None
    
    def get_source_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get source by name"""
        try:
            return self.db.news_sources.find_one({"name": name})
        except Exception as e:
            log_error_with_context(e, {'operation': 'get_source_by_name', 'name': name})
            return None
    
    def get_all_sources(self) -> List[Dict[str, Any]]:
        """Get all news sources"""
        try:
            return list(self.db.news_sources.find({}))
        except Exception as e:
            log_error_with_context(e, {'operation': 'get_all_sources'})
            return []
    
    def save_articles(self, source_id: str, articles: List[Dict[str, Any]]) -> bool:
        """Save articles for a source"""
        try:
            # Remove old articles for this source
            self.db.news_articles.delete_many({"search_id": source_id})
            
            # Get source info
            source = self.get_source_by_id(source_id)
            if not source:
                self.logger.error(f"Source not found: {source_id}")
                return False
            
            # Prepare article document
            article_doc = {
                "search_id": source_id,
                "name": source['name'],
                "lang": source['language'],
                "articles": articles,
                "updated_at": time.time()
            }
            
            self.db.news_articles.insert_one(article_doc)
            self.logger.info(f"Saved {len(articles)} articles for {source['name']}")
            return True
            
        except Exception as e:
            log_error_with_context(e, {
                'operation': 'save_articles',
                'source_id': source_id,
                'article_count': len(articles)
            })
            return False
    
    def get_articles_by_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get articles for a source"""
        try:
            return self.db.news_articles.find_one({"search_id": source_id})
        except Exception as e:
            log_error_with_context(e, {'operation': 'get_articles_by_source', 'source_id': source_id})
            return None


class NewsService:
    """High-level news service combining API and database operations"""

    def __init__(self):
        self.config = get_config()
        self.api_client = NewsAPIClient()
        self.database = NewsDatabase()
        self.tts_manager = TTSManager()
        self.logger = get_logger('news_service')
    
    def initialize_sources(self) -> bool:
        """Initialize news sources from API"""
        self.logger.info("Initializing news sources...")
        
        # Fetch sources from API
        sources_data = self.api_client.get_sources()
        if not sources_data or sources_data.get('status') != 'ok':
            self.logger.error("Failed to fetch sources from API")
            return False
        
        # Save to database
        sources = sources_data.get('sources', [])
        if self.database.save_sources(sources):
            self.logger.info(f"Successfully initialized {len(sources)} news sources")
            return True
        else:
            self.logger.error("Failed to save sources to database")
            return False
    
    def _is_google_news_source(self, source_id: str) -> bool:
        """Check if source is a Google News source"""
        return source_id.startswith('google-news')

    def _clean_google_news_title(self, title: str) -> str:
        """Remove source attribution from Google News titles"""
        # Google News titles often end with " - Source Name"
        # Remove everything after the last " - "
        if ' - ' in title:
            # Split by " - " and take all parts except the last one
            parts = title.rsplit(' - ', 1)
            return parts[0].strip()
        return title

    def _fetch_google_news_rss(self, source: dict) -> List[Dict[str, Any]]:
        """Fetch articles from Google News RSS feed"""
        try:
            # Extract country code from source_id (e.g., 'google-news-ca' -> 'CA')
            source_id = source['search_id']
            country_code = source_id.split('-')[-1].upper()
            language = source.get('language', 'en')

            # Build RSS URL
            rss_url = f"https://news.google.com/rss?hl={language}-{country_code}&gl={country_code}&ceid={country_code}:{language}"

            self.logger.info(f"Fetching Google News RSS from: {rss_url}")

            # Parse RSS feed
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                self.logger.warning(f"No entries found in Google News RSS feed for {source['name']}")
                return []

            # Convert RSS entries to NewsAPI format
            articles = []
            for entry in feed.entries[:20]:  # Limit to 20 articles
                # Clean the title to remove source attribution
                raw_title = entry.get('title', '')
                clean_title = self._clean_google_news_title(raw_title)

                article = {
                    'source': {
                        'id': source_id,
                        'name': source['name']
                    },
                    'title': clean_title,
                    'description': entry.get('summary', ''),
                    'url': entry.get('link', ''),
                    'publishedAt': entry.get('published', ''),
                    'content': entry.get('summary', '')
                }
                articles.append(article)

            self.logger.info(f"Fetched {len(articles)} articles from Google News RSS")
            return articles

        except Exception as e:
            self.logger.error(f"Error fetching Google News RSS: {e}")
            return []

    def fetch_and_store_articles(self, source_name: str) -> bool:
        """Fetch articles for a source and store them"""
        # Get source info
        source = self.database.get_source_by_name(source_name)
        if not source:
            self.logger.error(f"Source not found: {source_name}")
            return False

        # Check if this is a Google News source
        if self._is_google_news_source(source['search_id']):
            # Use RSS feed for Google News
            articles = self._fetch_google_news_rss(source)
            if not articles:
                self.logger.error(f"Failed to fetch articles from Google News RSS for {source_name}")
                return False
            return self.database.save_articles(source['search_id'], articles)
        else:
            # Use NewsAPI for other sources
            articles_data = self.api_client.get_headlines(source['search_id'])
            if not articles_data or articles_data.get('status') != 'ok':
                self.logger.error(f"Failed to fetch articles for {source_name}")
                return False

            # Store articles
            articles = articles_data.get('articles', [])
            return self.database.save_articles(source['search_id'], articles)

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
    
    def get_text_summary(self, source_name: str) -> str:
        """Generate text summary for a source"""
        source = self.database.get_source_by_name(source_name)
        if not source:
            return f"❌ Source '{source_name}' not found."

        articles_doc = self.database.get_articles_by_source(source['search_id'])
        if not articles_doc:
            return f"❌ No articles found for {source_name}. Try again later."

        articles = articles_doc.get('articles', [])
        if not articles:
            return f"❌ No articles available for {source_name}."

        # Get expected language for this source
        expected_language = source.get('language', 'en')

        # Build summary
        summary = f"*📰 {source_name} - Breaking Headlines*\n\n"

        valid_count = 0
        for article in articles:
            # Filter out invalid/generic articles
            if not self._is_valid_article(article, source_name, expected_language):
                continue

            if valid_count >= 10:  # Limit to 10 valid articles
                break

            title = article.get('title', 'No title')
            description = article.get('description', '')
            url = article.get('url', '')

            # Clean HTML from title and description
            title = self._strip_html(title)
            description = self._strip_html(description)

            # Add title with link
            if url:
                summary += f"• [{title}]({url})\n"
            else:
                summary += f"• {title}\n"

            # Add description if available (truncate if too long)
            # Don't use markdown formatting for description to avoid parsing errors
            if description:
                if len(description) > 200:
                    description = description[:200] + "..."
                summary += f"  {description}\n\n"
            else:
                summary += "\n"

            valid_count += 1

        # Check if we found any valid articles
        if valid_count == 0:
            return f"❌ No valid articles available for {source_name}. The source may have generic placeholder content."

        summary += "Check back later for updates! 📱"

        # Ensure summary doesn't exceed Telegram limits
        if len(summary) > self.config.max_summary_length:
            summary = summary[:self.config.max_summary_length - 50] + "...\n\n📱 Check back later for updates!"

        return summary
    
    def generate_audio_summary(self, source_name: str) -> Optional[str]:
        """Generate audio summary for a source"""
        source = self.database.get_source_by_name(source_name)
        if not source:
            self.logger.error(f"Source not found: {source_name}")
            return None

        articles_doc = self.database.get_articles_by_source(source['search_id'])
        if not articles_doc:
            self.logger.error(f"No articles found for {source_name}")
            return None

        articles = articles_doc.get('articles', [])
        if not articles:
            self.logger.error(f"No articles available for {source_name}")
            return None

        # Check if language is supported for TTS
        language = source.get('language', 'en')
        if language not in lang.tts_langs():
            self.logger.warning(f"Language {language} not supported for TTS")
            return None

        # Filter valid articles first
        valid_articles = [
            a for a in articles
            if self._is_valid_article(a, source_name, language)
        ]

        if not valid_articles:
            self.logger.warning(f"No valid articles for {source_name} after filtering")
            return None

        # Build audio script
        script = f"Recent headlines from {source_name} today are: "

        for article in valid_articles[:10]:  # Limit to 10 valid articles for audio (matching text summary)
            title = article.get('title', '')
            description = article.get('description', '')

            # Clean HTML from title and description
            title = self._strip_html(title)
            description = self._strip_html(description)

            if title:
                script += f"{title}. "
                if description and len(description) < 200:
                    script += f"{description}. "
                script += "In other news, "

        # Remove trailing "In other news, " before the closing
        if script.endswith("In other news, "):
            script = script[:-len("In other news, ")]

        script += "Check back later for updates."

        # Generate audio file
        audio_path = f"{self.config.tts.audio_output_dir}/{source_name}-summary.mp3"

        if self.tts_manager.generate_audio(script, language, audio_path, self.config.tts.preferred_engine):
            self.logger.info(f"Generated audio summary for {source_name}")
            return audio_path
        else:
            self.logger.error(f"Failed to generate audio for {source_name}")
            return None
