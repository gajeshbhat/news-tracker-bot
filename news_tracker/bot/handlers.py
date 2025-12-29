"""
Telegram bot handlers for News Tracker Bot
Modernized with proper async/await patterns and error handling
"""

import os
import asyncio
import concurrent.futures
from typing import Dict, Any

import telegram
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..api.news_client import NewsService
from ..utils.logging_config import get_logger, log_bot_interaction, log_error_with_context
from .user_sessions import UserSessionManager
from ..core.product_keys import ProductKeyManager


class NewsTrackerBot:
    """Main bot class with all handlers"""
    
    def __init__(self):
        self.logger = get_logger('bot')
        self.news_service = NewsService()
        self.session_manager = UserSessionManager()
        self.key_manager = ProductKeyManager()

        # Help text
        self.help_text = '''
*🤖 Welcome to News Tracker Bot*

*Commands:*
• `/start` - Welcome message and register your product key
• `/help` - Show this help
• `/latest` - Get latest news summaries
• `/schedule` - Manage automated news delivery schedules
• `/register KEY` - Register your product key

*How it works:*
1️⃣ Register your product key with `/register YOUR-KEY`
2️⃣ Send `/latest` to see available news sources
3️⃣ Choose a news source from the menu
4️⃣ Select format: Text, Audio, or Both
5️⃣ Get your personalized news summary!

*Scheduled Delivery:*
📅 Use `/schedule` to set up automated news delivery
⏰ Choose your preferred time and timezone
🗞️ Select up to 2 news sources per schedule
📊 Manage up to 5 active schedules

*Features:*
📰 Text summaries with clickable links
🔊 High-quality audio summaries
🌍 Multiple languages and timezones supported
⚡ Real-time news updates
🔔 Automated scheduled delivery

*Powered by NewsAPI.org*
        '''
    
    def _is_user_authorized(self, user_id: int) -> bool:
        """Check if user has a valid product key"""
        # Check if user has an active key assigned
        keys = self.key_manager.list_keys(active_only=True)
        for key in keys:
            if key.user_id == user_id:
                return True
        return False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        try:
            # Check if user is authorized
            if self._is_user_authorized(user_id):
                await update.message.reply_text(
                    "👋 Hello! Welcome back to News Tracker Bot.\n\n"
                    "I can provide you with the latest news summaries in both text and audio formats.\n\n"
                    "Type /help to see available commands or /latest to get started!"
                )
            else:
                await update.message.reply_text(
                    "👋 Hello! Welcome to News Tracker Bot.\n\n"
                    "🔐 To use this bot, you need a product key.\n\n"
                    "Please register your key using:\n"
                    "`/register YOUR-PRODUCT-KEY`\n\n"
                    "Contact the administrator to get a product key.",
                    parse_mode=ParseMode.MARKDOWN
                )

            log_bot_interaction(user_id, '/start', True)
            self.logger.info(f"New user started bot: {user_id}")

        except Exception as e:
            log_error_with_context(e, {'command': '/start', 'user_id': user_id})
            log_bot_interaction(user_id, '/start', False)
    
    async def register_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /register command"""
        user_id = update.effective_user.id
        username = update.effective_user.username

        try:
            # Get the product key from command arguments
            if not context.args or len(context.args) == 0:
                await update.message.reply_text(
                    "❌ Please provide a product key.\n\n"
                    "Usage: `/register YOUR-PRODUCT-KEY`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            product_key = context.args[0]

            # Validate the key
            key_obj = self.key_manager.validate_key(product_key)

            if not key_obj:
                await update.message.reply_text(
                    "❌ Invalid or expired product key.\n\n"
                    "Please check your key and try again, or contact the administrator."
                )
                log_bot_interaction(user_id, '/register', False)
                return

            # Check if key is already assigned to another user
            if key_obj.user_id and key_obj.user_id != user_id:
                await update.message.reply_text(
                    "❌ This product key is already assigned to another user."
                )
                log_bot_interaction(user_id, '/register', False)
                return

            # Assign key to user
            if self.key_manager.assign_key_to_user(product_key, user_id, username):
                await update.message.reply_text(
                    "✅ Product key registered successfully!\n\n"
                    "You can now use the bot. Type /latest to get started!"
                )
                log_bot_interaction(user_id, '/register', True)
                self.logger.info(f"User {user_id} ({username}) registered with product key")
            else:
                await update.message.reply_text(
                    "❌ Failed to register product key. Please try again later."
                )
                log_bot_interaction(user_id, '/register', False)

        except Exception as e:
            log_error_with_context(e, {'command': '/register', 'user_id': user_id})
            log_bot_interaction(user_id, '/register', False)
            await update.message.reply_text(
                "❌ An error occurred. Please try again later."
            )

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
            # Check authorization
            if not self._is_user_authorized(user_id):
                await update.message.reply_text(
                    "🔐 You need to register a product key first.\n\n"
                    "Use: `/register YOUR-PRODUCT-KEY`\n\n"
                    "Contact the administrator to get a product key.",
                    parse_mode=ParseMode.MARKDOWN
                )
                log_bot_interaction(user_id, '/latest', False)
                return

            # Get available news sources
            sources = self.news_service.database.get_all_sources()

            if not sources:
                await update.message.reply_text(
                    "❌ No news sources available. Please try again later."
                )
                log_bot_interaction(user_id, '/latest', False)
                return

            # Initialize pagination
            context.user_data['latest_page'] = 0
            context.user_data['all_sources'] = sources

            # Show first page
            await self._show_source_page(update, context, is_new_message=True)

            log_bot_interaction(user_id, '/latest', True)

        except Exception as e:
            log_error_with_context(e, {'command': '/latest', 'user_id': user_id})
            log_bot_interaction(user_id, '/latest', False)
            await update.message.reply_text(
                "❌ Sorry, something went wrong. Please try again later."
            )

    async def _show_source_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_new_message: bool = False):
        """Show a page of news sources with pagination"""
        sources = context.user_data.get('all_sources', [])
        page = context.user_data.get('latest_page', 0)

        sources_per_page = 10
        start_idx = page * sources_per_page
        end_idx = start_idx + sources_per_page

        # Create keyboard with sources
        keyboard = []
        for source in sources[start_idx:end_idx]:
            keyboard.append([
                InlineKeyboardButton(
                    source['name'],
                    callback_data=f"latest_source_{source['search_id']}"
                )
            ])

        # Navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton("⬅️ Previous", callback_data="latest_prev")
            )
        if end_idx < len(sources):
            nav_buttons.append(
                InlineKeyboardButton("Next ➡️", callback_data="latest_next")
            )

        if nav_buttons:
            keyboard.append(nav_buttons)

        # Cancel button
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="latest_cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Show page info
        total_pages = (len(sources) + sources_per_page - 1) // sources_per_page
        text = f"📰 *Choose a news source:*\n\nPage {page + 1} of {total_pages} ({len(sources)} sources total)"

        if is_new_message:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    async def handle_latest_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from /latest pagination and source selection"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        data = query.data

        try:
            if data == "latest_prev":
                # Go to previous page
                context.user_data['latest_page'] = context.user_data.get('latest_page', 0) - 1
                await self._show_source_page(update, context, is_new_message=False)

            elif data == "latest_next":
                # Go to next page
                context.user_data['latest_page'] = context.user_data.get('latest_page', 0) + 1
                await self._show_source_page(update, context, is_new_message=False)

            elif data == "latest_cancel":
                # Cancel and clear data
                context.user_data.pop('latest_page', None)
                context.user_data.pop('all_sources', None)
                await query.edit_message_text("❌ Action cancelled.")

            elif data.startswith("latest_source_"):
                # Source selected
                source_id = data.replace("latest_source_", "")

                # Get source info
                sources = context.user_data.get('all_sources', [])
                source = next((s for s in sources if s['search_id'] == source_id), None)

                if not source:
                    await query.edit_message_text("❌ Source not found. Please try /latest again.")
                    return

                source_name = source['name']

                # Clear pagination data
                context.user_data.pop('latest_page', None)
                context.user_data.pop('all_sources', None)

                # Handle source selection (show format options)
                await self._handle_source_selection_inline(update, source_name)

        except Exception as e:
            log_error_with_context(e, {
                'handler': 'handle_latest_callback',
                'user_id': user_id,
                'callback_data': data
            })
            await query.edit_message_text(
                "❌ Sorry, something went wrong. Please try /latest again."
            )

    async def _handle_source_selection_inline(self, update: Update, source_name: str):
        """Handle source selection from inline keyboard"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        # Verify source exists
        source = self.news_service.database.get_source_by_name(source_name)
        if not source:
            await query.edit_message_text(
                f"❌ Unknown source: {source_name}\n"
                "Please try /latest again."
            )
            return

        # Create session
        self.session_manager.create_session(chat_id, source_name)

        # Show format selection with inline keyboard
        keyboard = [
            [InlineKeyboardButton("📰 Text Summary", callback_data="format_text")],
            [InlineKeyboardButton("🔊 Audio Summary", callback_data="format_audio")],
            [InlineKeyboardButton("📰🔊 Both", callback_data="format_both")],
            [InlineKeyboardButton("❌ Cancel", callback_data="format_cancel")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"📰 Selected: *{source_name}*\n\n"
            "Choose your preferred format:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def handle_format_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle format selection callbacks"""
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        data = query.data

        try:
            if data == "format_cancel":
                # Cancel and clear session
                self.session_manager.clear_session(chat_id)
                await query.edit_message_text("❌ Action cancelled.")
                return

            # Get session
            session = self.session_manager.get_session(chat_id)
            if not session:
                await query.edit_message_text(
                    "❌ Session expired. Please try /latest again."
                )
                return

            source_name = session['source_name']

            # Determine format
            if data == "format_text":
                format_choice = "Text Summary"
            elif data == "format_audio":
                format_choice = "Audio Summary"
            elif data == "format_both":
                format_choice = "Both"
            else:
                await query.edit_message_text("❌ Invalid format. Please try again.")
                return

            # Delete the format selection message
            await query.delete_message()

            # Send news using the callback query's message context
            if format_choice == "Text Summary":
                await self._send_text_summary_callback(query, source_name)
            elif format_choice == "Audio Summary":
                await self._send_audio_summary_callback(query, source_name)
            elif format_choice == "Both":
                await self._send_text_summary_callback(query, source_name)
                await self._send_audio_summary_callback(query, source_name)

            # Clear session
            self.session_manager.clear_session(chat_id)
            log_bot_interaction(user_id, f'format_selected:{format_choice}', True)

        except Exception as e:
            log_error_with_context(e, {
                'handler': 'handle_format_callback',
                'user_id': user_id,
                'callback_data': data
            })
            await query.edit_message_text(
                "❌ Sorry, something went wrong. Please try /latest again."
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

    async def _send_text_summary_callback(self, query, source_name: str):
        """Send text summary from callback query"""
        try:
            # Show loading message
            status_msg = await query.message.reply_text("📰 Fetching latest news...")

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
            await query.message.reply_text(
                text=summary,
                disable_web_page_preview=True,
                parse_mode=ParseMode.MARKDOWN
            )

            # Delete status message
            await status_msg.delete()

        except Exception as e:
            log_error_with_context(e, {'operation': 'send_text_summary_callback', 'source': source_name})
            await query.message.reply_text(
                f"❌ Sorry, couldn't fetch news for {source_name}. Please try again later."
            )

    async def _send_audio_summary_callback(self, query, source_name: str):
        """Send audio summary from callback query"""
        try:
            # Show loading message
            status_msg = await query.message.reply_text("🔊 Generating audio summary...")

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
                    await query.message.reply_audio(
                        audio=audio_file,
                        caption=f"🔊 Audio summary: {source_name}"
                    )

                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ Audio summary not available for this source.")

        except Exception as e:
            log_error_with_context(e, {'operation': 'send_audio_summary_callback', 'source': source_name})
            await query.message.reply_text(
                f"❌ Sorry, couldn't generate audio for {source_name}. Please try again later."
            )
