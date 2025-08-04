"""
Telegram bot handlers for News Tracker Bot
Modernized with proper async/await patterns and error handling
"""

import os
import asyncio
import concurrent.futures
from typing import Dict, Any

import telegram
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..api.news_client import NewsService
from ..utils.logging_config import get_logger, log_bot_interaction, log_error_with_context
from .user_sessions import UserSessionManager


class NewsTrackerBot:
    """Main bot class with all handlers"""
    
    def __init__(self):
        self.logger = get_logger('bot')
        self.news_service = NewsService()
        self.session_manager = UserSessionManager()
        
        # Help text
        self.help_text = '''
*🤖 Welcome to News Tracker Bot*

*Commands:*
• `/start` - Welcome message
• `/help` - Show this help
• `/latest` - Get latest news summaries

*How it works:*
1️⃣ Send `/latest` to see available news sources
2️⃣ Choose a news source from the menu
3️⃣ Select format: Text, Audio, or Both
4️⃣ Get your personalized news summary!

*Features:*
📰 Text summaries with clickable links
🔊 High-quality audio summaries
🌍 Multiple languages supported
⚡ Real-time news updates

*Powered by NewsAPI.org*
        '''
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        try:
            await update.message.reply_text(
                "👋 Hello! Welcome to News Tracker Bot.\n\n"
                "I can provide you with the latest news summaries in both text and audio formats.\n\n"
                "Type /help to see available commands or /latest to get started!"
            )
            
            log_bot_interaction(user_id, '/start', True)
            self.logger.info(f"New user started bot: {user_id}")
            
        except Exception as e:
            log_error_with_context(e, {'command': '/start', 'user_id': user_id})
            log_bot_interaction(user_id, '/start', False)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user_id = update.effective_user.id
        
        try:
            await update.message.reply_text(
                text=self.help_text,
                disable_web_page_preview=True,
                parse_mode=ParseMode.MARKDOWN
            )
            
            log_bot_interaction(user_id, '/help', True)
            
        except Exception as e:
            log_error_with_context(e, {'command': '/help', 'user_id': user_id})
            log_bot_interaction(user_id, '/help', False)
    
    async def latest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /latest command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        try:
            # Get available news sources
            sources = self.news_service.database.get_all_sources()
            
            if not sources:
                await update.message.reply_text(
                    "❌ No news sources available. Please try again later."
                )
                log_bot_interaction(user_id, '/latest', False)
                return
            
            # Create keyboard with source names
            source_names = [source['name'] for source in sources[:20]]  # Limit to 20
            keyboard = []
            
            # Create rows of 2 buttons each
            for i in range(0, len(source_names), 2):
                row = source_names[i:i+2]
                keyboard.append(row)
            
            # Add cancel button
            keyboard.append(['Cancel'])
            
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "📰 Choose a news source:",
                reply_markup=reply_markup
            )
            
            log_bot_interaction(user_id, '/latest', True)
            
        except Exception as e:
            log_error_with_context(e, {'command': '/latest', 'user_id': user_id})
            log_bot_interaction(user_id, '/latest', False)
            await update.message.reply_text(
                "❌ Sorry, something went wrong. Please try again later."
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (source selection and format selection)"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        message_text = update.message.text
        
        try:
            if message_text == "Cancel":
                await self._handle_cancel(update)
                return
            
            # Check if user has an active session
            session = self.session_manager.get_session(chat_id)
            
            if not session:
                # User selected a news source
                await self._handle_source_selection(update, message_text)
            else:
                # User selected a format
                await self._handle_format_selection(update, message_text)
                
        except Exception as e:
            log_error_with_context(e, {
                'handler': 'handle_message',
                'user_id': user_id,
                'message': message_text
            })
            await update.message.reply_text(
                "❌ Sorry, something went wrong. Please try again."
            )
    
    async def _handle_cancel(self, update: Update):
        """Handle cancel action"""
        chat_id = update.effective_chat.id
        
        # Clear session
        self.session_manager.clear_session(chat_id)
        
        reply_markup = ReplyKeyboardRemove()
        await update.message.reply_text(
            "❌ Action cancelled.",
            reply_markup=reply_markup
        )
    
    async def _handle_source_selection(self, update: Update, source_name: str):
        """Handle news source selection"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Verify source exists
        source = self.news_service.database.get_source_by_name(source_name)
        if not source:
            await update.message.reply_text(
                f"❌ Unknown source: {source_name}\n"
                "Please select from the available options or type /latest to start over."
            )
            return
        
        # Create session
        self.session_manager.create_session(chat_id, source_name)
        
        # Check audio availability
        language = source.get('language', 'en')
        audio_available = self.news_service.tts_manager.is_language_supported(language)
        
        # Create format options
        options = [["Text Summary"]]
        if audio_available:
            options.extend([["Audio Summary"], ["Both"]])
        options.append(["Cancel"])
        
        reply_markup = ReplyKeyboardMarkup(options, resize_keyboard=True)
        
        await update.message.reply_text(
            f"📰 Selected: *{source_name}*\n\n"
            "Choose the format for your news summary:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        log_bot_interaction(user_id, f'source_selected:{source_name}', True)
    
    async def _handle_format_selection(self, update: Update, format_choice: str):
        """Handle format selection"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        session = self.session_manager.get_session(chat_id)
        if not session:
            await update.message.reply_text("❌ Session expired. Please start over with /latest")
            return
        
        source_name = session['source_name']
        
        try:
            if format_choice == "Text Summary":
                await self._send_text_summary(update, source_name)
            elif format_choice == "Audio Summary":
                await self._send_audio_summary(update, source_name)
            elif format_choice == "Both":
                await self._send_text_summary(update, source_name)
                await self._send_audio_summary(update, source_name)
            else:
                await update.message.reply_text(
                    "❌ Invalid option. Please choose from the available formats."
                )
                return
            
            log_bot_interaction(user_id, f'format_selected:{format_choice}', True)
            
        finally:
            # Clear session and remove keyboard
            self.session_manager.clear_session(chat_id)
    
    async def _send_text_summary(self, update: Update, source_name: str):
        """Send text summary"""
        try:
            # Show loading message
            status_msg = await update.message.reply_text("📰 Fetching latest news...")
            
            # Fetch and store articles in background
            def fetch_articles():
                return self.news_service.fetch_and_store_articles(source_name)
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                success = await loop.run_in_executor(executor, fetch_articles)
            
            if not success:
                await status_msg.edit_text("❌ Failed to fetch news. Please try again later.")
                return
            
            # Generate summary
            summary = self.news_service.get_text_summary(source_name)
            
            # Send summary
            reply_markup = ReplyKeyboardRemove()
            await update.message.reply_text(
                text=summary,
                disable_web_page_preview=True,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            # Delete status message
            await status_msg.delete()
            
        except Exception as e:
            log_error_with_context(e, {'operation': 'send_text_summary', 'source': source_name})
            await update.message.reply_text(
                f"❌ Sorry, couldn't fetch news for {source_name}. Please try again later.",
                reply_markup=ReplyKeyboardRemove()
            )
    
    async def _send_audio_summary(self, update: Update, source_name: str):
        """Send audio summary"""
        try:
            # Show loading message
            status_msg = await update.message.reply_text("🔊 Generating audio summary...")
            
            # Generate audio in background
            def generate_audio():
                # Ensure articles are fetched
                self.news_service.fetch_and_store_articles(source_name)
                # Generate audio
                return self.news_service.generate_audio_summary(source_name)
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                audio_path = await loop.run_in_executor(executor, generate_audio)
            
            if audio_path and os.path.exists(audio_path):
                await status_msg.edit_text("🔊 Audio ready! Sending...")
                
                with open(audio_path, 'rb') as audio_file:
                    await update.message.reply_audio(
                        audio=audio_file,
                        caption=f"🔊 Audio summary: {source_name}"
                    )
                
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ Audio summary not available for this source.")
            
        except Exception as e:
            log_error_with_context(e, {'operation': 'send_audio_summary', 'source': source_name})
            await update.message.reply_text(
                f"❌ Sorry, couldn't generate audio for {source_name}. Please try again later."
            )
