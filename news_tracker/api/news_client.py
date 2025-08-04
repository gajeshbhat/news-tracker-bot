"""
News API client for fetching news data
Modernized version with proper error handling and logging
"""

import requests
import time
from typing import Dict, List, Optional, Any
from pymongo import MongoClient
from gtts import lang

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
    
    def fetch_and_store_articles(self, source_name: str) -> bool:
        """Fetch articles for a source and store them"""
        # Get source info
        source = self.database.get_source_by_name(source_name)
        if not source:
            self.logger.error(f"Source not found: {source_name}")
            return False
        
        # Fetch articles from API
        articles_data = self.api_client.get_headlines(source['search_id'])
        if not articles_data or articles_data.get('status') != 'ok':
            self.logger.error(f"Failed to fetch articles for {source_name}")
            return False
        
        # Store articles
        articles = articles_data.get('articles', [])
        return self.database.save_articles(source['search_id'], articles)
    
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
        
        # Build summary
        summary = f"*📰 {source_name} - Breaking Headlines*\n\n"
        
        for article in articles[:10]:  # Limit to 10 articles
            title = article.get('title', 'No title')
            url = article.get('url', '')
            
            if url:
                summary += f"• [{title}]({url})\n\n"
            else:
                summary += f"• {title}\n\n"
        
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
        
        # Build audio script
        script = f"Recent headlines from {source_name} today are: "
        
        for article in articles[:5]:  # Limit to 5 articles for audio
            title = article.get('title', '')
            description = article.get('description', '')
            
            if title:
                script += f"{title}. "
                if description and len(description) < 200:
                    script += f"{description}. "
                script += "In other news, "
        
        script += "Check back later for updates."
        
        # Generate audio file
        audio_path = f"{self.config.tts.audio_output_dir}/{source_name}-summary.mp3"
        
        if self.tts_manager.generate_audio(script, language, audio_path, self.config.tts.preferred_engine):
            self.logger.info(f"Generated audio summary for {source_name}")
            return audio_path
        else:
            self.logger.error(f"Failed to generate audio for {source_name}")
            return None
