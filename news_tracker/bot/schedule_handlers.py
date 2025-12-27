"""
Schedule Handlers for News Tracker Bot

Handles /schedule command and all scheduling-related interactions.
"""

import logging
from datetime import datetime
from typing import Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from news_tracker.core.schedule_manager import ScheduleManager
from news_tracker.core.product_keys import ProductKeyManager
from news_tracker.core.config import get_config, AppConfig
from news_tracker.api.news_client import NewsService


# Conversation states
(
    SCHEDULE_MENU,
    SELECT_SOURCES,
    SELECT_FORMAT,
    SELECT_TIME_PRESET,
    SELECT_CUSTOM_TIME,
    SELECT_TIMEZONE,
    SELECT_FREQUENCY,
    CONFIRM_SCHEDULE,
    VIEW_SCHEDULES,
    EDIT_SCHEDULE,
) = range(10)

# Callback data prefixes
SCHEDULE_PREFIX = "sched_"
SOURCE_PREFIX = "src_"
FORMAT_PREFIX = "fmt_"
TIME_PREFIX = "time_"
TZ_PREFIX = "tz_"
FREQ_PREFIX = "freq_"


class ScheduleHandlers:
    """Handles all schedule-related bot interactions"""

    def __init__(self, config: AppConfig):
        """
        Initialize schedule handlers

        Args:
            config: Bot configuration
        """
        self.config = config
        self.schedule_manager = ScheduleManager(config.database.mongo_uri)
        self.key_manager = ProductKeyManager(config.database.mongo_uri)
        self.news_service = NewsService()
        self.logger = logging.getLogger(__name__)

        # Temporary storage for schedule creation (user_id -> data)
        self.temp_schedules: Dict[int, Dict] = {}

    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /schedule command - entry point
        """
        user = update.effective_user

        # Check if user is registered
        product_key = self.key_manager.get_key_by_user_id(user.id)
        if not product_key or not product_key.is_active:
            await update.message.reply_text(
                "🔐 You need to register first!\n\n"
                "Use /register YOUR-PRODUCT-KEY to get started."
            )
            return ConversationHandler.END

        # Show main schedule menu
        return await self._show_schedule_menu(update, context)

    async def _show_schedule_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the main schedule menu"""
        user = update.effective_user

        # Count user's schedules
        schedule_count = self.schedule_manager.count_user_schedules(user.id)
        max_schedules = 5

        keyboard = []

        # Create new schedule (if under limit)
        if schedule_count < max_schedules:
            keyboard.append([
                InlineKeyboardButton(
                    "➕ Create New Schedule",
                    callback_data=f"{SCHEDULE_PREFIX}create"
                )
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(
                    f"⚠️ Limit Reached ({max_schedules}/{max_schedules})",
                    callback_data=f"{SCHEDULE_PREFIX}limit"
                )
            ])

        # View schedules (if any exist)
        if schedule_count > 0:
            keyboard.append([
                InlineKeyboardButton(
                    f"📋 View My Schedules ({schedule_count})",
                    callback_data=f"{SCHEDULE_PREFIX}view"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("❌ Cancel", callback_data=f"{SCHEDULE_PREFIX}cancel")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "📅 *Schedule News Delivery*\n\n"
            f"You have {schedule_count}/{max_schedules} active schedules.\n\n"
            "Scheduled deliveries allow you to receive news automatically "
            "at your preferred time each day.\n\n"
            "What would you like to do?"
        )

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        return SCHEDULE_MENU

    async def handle_schedule_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle schedule menu selections"""
        query = update.callback_query
        await query.answer()

        data = query.data.replace(SCHEDULE_PREFIX, "")

        if data == "create":
            return await self._start_create_schedule(update, context)
        elif data == "view":
            return await self._view_schedules(update, context)
        elif data == "limit":
            await query.answer("You've reached the maximum of 5 schedules. Delete one to create a new one.", show_alert=True)
            return SCHEDULE_MENU
        elif data == "cancel":
            await query.edit_message_text("❌ Cancelled.")
            return ConversationHandler.END

        return SCHEDULE_MENU

    async def _start_create_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the schedule creation flow"""
        user = update.effective_user

        # Initialize temp storage
        self.temp_schedules[user.id] = {
            'sources': [],
            'format': None,
            'time': None,
            'timezone': None,
            'frequency': None
        }

        return await self._show_source_selection(update, context)

    async def _show_source_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show source selection menu"""
        user = update.effective_user
        selected_sources = self.temp_schedules.get(user.id, {}).get('sources', [])

        # Get available sources from database
        sources_data = self.news_service.database.get_all_sources()

        if not sources_data:
            await update.callback_query.answer("❌ No news sources available. Please contact administrator.")
            return ConversationHandler.END

        # Create keyboard with sources (paginated if needed)
        keyboard = []
        sources_per_page = 10
        page = context.user_data.get('source_page', 0)
        start_idx = page * sources_per_page
        end_idx = start_idx + sources_per_page

        for source in sources_data[start_idx:end_idx]:
            source_id = source['search_id']
            source_name = source['name']

            # Show checkmark if selected
            prefix = "✓ " if source_id in selected_sources else ""

            keyboard.append([
                InlineKeyboardButton(
                    f"{prefix}{source_name}",
                    callback_data=f"{SOURCE_PREFIX}{source_id}"
                )
            ])

        # Navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton("⬅️ Previous", callback_data=f"{SOURCE_PREFIX}prev")
            )
        if end_idx < len(sources_data):
            nav_buttons.append(
                InlineKeyboardButton("Next ➡️", callback_data=f"{SOURCE_PREFIX}next")
            )

        if nav_buttons:
            keyboard.append(nav_buttons)

        # Action buttons
        action_buttons = []
        if selected_sources:
            action_buttons.append(
                InlineKeyboardButton("Next ➡️", callback_data=f"{SOURCE_PREFIX}done")
            )
        action_buttons.append(
            InlineKeyboardButton("❌ Cancel", callback_data=f"{SOURCE_PREFIX}cancel")
        )
        keyboard.append(action_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)

        selected_count = len(selected_sources)
        text = (
            "🗞️ *Select News Sources*\n\n"
            f"Selected: {selected_count}/2\n\n"
            "Choose up to 2 news sources for your scheduled delivery.\n"
            "Tap a source to select/deselect it."
        )

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        return SELECT_SOURCES

    async def handle_source_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle source selection"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        data = query.data.replace(SOURCE_PREFIX, "")

        if data == "prev":
            context.user_data['source_page'] = context.user_data.get('source_page', 0) - 1
            return await self._show_source_selection(update, context)
        elif data == "next":
            context.user_data['source_page'] = context.user_data.get('source_page', 0) + 1
            return await self._show_source_selection(update, context)
        elif data == "done":
            if not self.temp_schedules[user.id]['sources']:
                await query.answer("Please select at least one source!", show_alert=True)
                return SELECT_SOURCES
            return await self._show_format_selection(update, context)
        elif data == "cancel":
            self.temp_schedules.pop(user.id, None)
            await query.edit_message_text("❌ Cancelled.")
            return ConversationHandler.END
        else:
            # Toggle source selection
            source_id = data
            selected = self.temp_schedules[user.id]['sources']

            if source_id in selected:
                selected.remove(source_id)
            else:
                if len(selected) >= 2:
                    await query.answer("Maximum 2 sources allowed!", show_alert=True)
                    return SELECT_SOURCES
                selected.append(source_id)

            return await self._show_source_selection(update, context)

    async def _show_format_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show format selection menu"""
        keyboard = [
            [InlineKeyboardButton("📰 Text Summary", callback_data=f"{FORMAT_PREFIX}text")],
            [InlineKeyboardButton("🔊 Audio Summary", callback_data=f"{FORMAT_PREFIX}audio")],
            [InlineKeyboardButton("📰🔊 Both (Text + Audio)", callback_data=f"{FORMAT_PREFIX}both")],
            [InlineKeyboardButton("⬅️ Back", callback_data=f"{FORMAT_PREFIX}back")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"{FORMAT_PREFIX}cancel")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "📰 *Select Delivery Format*\n\n"
            "How would you like to receive your news?\n\n"
            "• *Text Summary*: Articles with links\n"
            "• *Audio Summary*: AI-generated audio file\n"
            "• *Both*: Text and audio in the same message"
        )

        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        return SELECT_FORMAT

    async def handle_format_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle format selection"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        data = query.data.replace(FORMAT_PREFIX, "")

        if data == "back":
            return await self._show_source_selection(update, context)
        elif data == "cancel":
            self.temp_schedules.pop(user.id, None)
            await query.edit_message_text("❌ Cancelled.")
            return ConversationHandler.END
        else:
            # Save format
            self.temp_schedules[user.id]['format'] = data
            return await self._show_time_selection(update, context)

    async def _show_time_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show time preset selection"""
        keyboard = [
            [InlineKeyboardButton("🌅 Morning (8:00 AM)", callback_data=f"{TIME_PREFIX}08:00")],
            [InlineKeyboardButton("☀️ Noon (12:00 PM)", callback_data=f"{TIME_PREFIX}12:00")],
            [InlineKeyboardButton("🌆 Evening (6:00 PM)", callback_data=f"{TIME_PREFIX}18:00")],
            [InlineKeyboardButton("🌙 Night (10:00 PM)", callback_data=f"{TIME_PREFIX}22:00")],
            [InlineKeyboardButton("⏱️ Custom Time...", callback_data=f"{TIME_PREFIX}custom")],
            [InlineKeyboardButton("⬅️ Back", callback_data=f"{TIME_PREFIX}back")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"{TIME_PREFIX}cancel")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "⏰ *Select Delivery Time*\n\n"
            "When would you like to receive your news?\n\n"
            "Choose a preset time or enter a custom time."
        )

        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        return SELECT_TIME_PRESET

    async def handle_time_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle time preset selection"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        data = query.data.replace(TIME_PREFIX, "")

        if data == "back":
            return await self._show_format_selection(update, context)
        elif data == "cancel":
            self.temp_schedules.pop(user.id, None)
            await query.edit_message_text("❌ Cancelled.")
            return ConversationHandler.END
        elif data == "custom":
            await query.edit_message_text(
                "⏱️ *Enter Custom Time*\n\n"
                "Please enter the time in 24-hour format (HH:MM)\n\n"
                "Examples:\n"
                "• 09:30 (9:30 AM)\n"
                "• 14:45 (2:45 PM)\n"
                "• 23:00 (11:00 PM)",
                parse_mode='Markdown'
            )
            return SELECT_CUSTOM_TIME
        else:
            # Save preset time
            self.temp_schedules[user.id]['time'] = data
            return await self._show_timezone_selection(update, context)

    async def handle_custom_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle custom time input"""
        user = update.effective_user
        time_str = update.message.text.strip()

        # Validate time format
        try:
            hour, minute = map(int, time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError

            # Format as HH:MM
            formatted_time = f"{hour:02d}:{minute:02d}"
            self.temp_schedules[user.id]['time'] = formatted_time

            # Show timezone selection
            return await self._show_timezone_selection(update, context)

        except (ValueError, AttributeError):
            await update.message.reply_text(
                "❌ Invalid time format!\n\n"
                "Please enter time in HH:MM format (e.g., 09:30 or 14:45)"
            )
            return SELECT_CUSTOM_TIME

    async def _show_timezone_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show timezone selection menu"""
        timezones = ScheduleManager.get_available_timezones()

        # Paginate timezones
        page = context.user_data.get('tz_page', 0)
        tz_per_page = 8
        start_idx = page * tz_per_page
        end_idx = start_idx + tz_per_page

        keyboard = []

        for tz_id, tz_name in timezones[start_idx:end_idx]:
            keyboard.append([
                InlineKeyboardButton(tz_name, callback_data=f"{TZ_PREFIX}{tz_id}")
            ])

        # Navigation
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton("⬅️ Previous", callback_data=f"{TZ_PREFIX}prev")
            )
        if end_idx < len(timezones):
            nav_buttons.append(
                InlineKeyboardButton("Next ➡️", callback_data=f"{TZ_PREFIX}next")
            )

        if nav_buttons:
            keyboard.append(nav_buttons)

        keyboard.append([
            InlineKeyboardButton("⬅️ Back", callback_data=f"{TZ_PREFIX}back"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"{TZ_PREFIX}cancel")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "🌍 *Select Your Timezone*\n\n"
            "Choose your timezone so we can deliver news at the right time.\n\n"
            f"Page {page + 1}/{(len(timezones) + tz_per_page - 1) // tz_per_page}"
        )

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        return SELECT_TIMEZONE
    async def handle_timezone_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle timezone selection"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        data = query.data.replace(TZ_PREFIX, "")

        if data == "prev":
            context.user_data['tz_page'] = context.user_data.get('tz_page', 0) - 1
            return await self._show_timezone_selection(update, context)
        elif data == "next":
            context.user_data['tz_page'] = context.user_data.get('tz_page', 0) + 1
            return await self._show_timezone_selection(update, context)
        elif data == "back":
            return await self._show_time_selection(update, context)
        elif data == "cancel":
            self.temp_schedules.pop(user.id, None)
            await query.edit_message_text("❌ Cancelled.")
            return ConversationHandler.END
        else:
            # Save timezone
            self.temp_schedules[user.id]['timezone'] = data
            return await self._show_frequency_selection(update, context)

    async def _show_frequency_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show frequency selection menu"""
        keyboard = [
            [InlineKeyboardButton("📅 Daily", callback_data=f"{FREQ_PREFIX}daily")],
            [InlineKeyboardButton("💼 Weekdays Only (Mon-Fri)", callback_data=f"{FREQ_PREFIX}weekdays")],
            [InlineKeyboardButton("🏖️ Weekends Only (Sat-Sun)", callback_data=f"{FREQ_PREFIX}weekends")],
            [InlineKeyboardButton("⬅️ Back", callback_data=f"{FREQ_PREFIX}back")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"{FREQ_PREFIX}cancel")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "📆 *Select Delivery Frequency*\n\n"
            "How often would you like to receive news?\n\n"
            "• *Daily*: Every day\n"
            "• *Weekdays*: Monday through Friday\n"
            "• *Weekends*: Saturday and Sunday\n\n"
            "Note: Maximum once per day for scheduled deliveries."
        )

        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        return SELECT_FREQUENCY

    async def handle_frequency_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle frequency selection"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        data = query.data.replace(FREQ_PREFIX, "")

        if data == "back":
            return await self._show_timezone_selection(update, context)
        elif data == "cancel":
            self.temp_schedules.pop(user.id, None)
            await query.edit_message_text("❌ Cancelled.")
            return ConversationHandler.END
        else:
            # Save frequency
            self.temp_schedules[user.id]['frequency'] = data
            return await self._show_confirmation(update, context)

    async def _show_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show schedule confirmation"""
        user = update.effective_user
        schedule_data = self.temp_schedules[user.id]

        # Get source names from database
        all_sources = self.news_service.database.get_all_sources()
        source_names = [
            s['name'] for s in all_sources if s['search_id'] in schedule_data['sources']
        ]

        # Format display
        format_display = {
            'text': '📰 Text Summary',
            'audio': '🔊 Audio Summary',
            'both': '📰🔊 Both (Text + Audio)'
        }

        frequency_display = {
            'daily': '📅 Daily',
            'weekdays': '💼 Weekdays (Mon-Fri)',
            'weekends': '🏖️ Weekends (Sat-Sun)'
        }

        # Get timezone display name
        timezones = ScheduleManager.get_available_timezones()
        tz_display = next(
            (name for tz_id, name in timezones if tz_id == schedule_data['timezone']),
            schedule_data['timezone']
        )

        text = (
            "✅ *Confirm Your Schedule*\n\n"
            f"📋 *Summary:*\n"
            f"• Sources: {', '.join(source_names)}\n"
            f"• Format: {format_display[schedule_data['format']]}\n"
            f"• Time: {schedule_data['time']}\n"
            f"• Timezone: {tz_display}\n"
            f"• Frequency: {frequency_display[schedule_data['frequency']]}\n\n"
            "You'll receive your first delivery at the next scheduled time.\n\n"
            "Is this correct?"
        )

        keyboard = [
            [InlineKeyboardButton("✅ Confirm & Create", callback_data=f"{SCHEDULE_PREFIX}confirm")],
            [InlineKeyboardButton("⬅️ Back", callback_data=f"{SCHEDULE_PREFIX}conf_back")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"{SCHEDULE_PREFIX}conf_cancel")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        return CONFIRM_SCHEDULE

    async def handle_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle schedule confirmation"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        data = query.data.replace(SCHEDULE_PREFIX, "")

        if data == "confirm":
            # Create the schedule
            schedule_data = self.temp_schedules[user.id]

            schedule = self.schedule_manager.create_schedule(
                user_id=user.id,
                username=user.username,
                sources=schedule_data['sources'],
                format=schedule_data['format'],
                time_str=schedule_data['time'],
                timezone=schedule_data['timezone'],
                frequency=schedule_data['frequency']
            )

            if schedule:
                # Clean up temp data
                self.temp_schedules.pop(user.id, None)

                # Format next send time in user's timezone
                import pytz
                tz = pytz.timezone(schedule.timezone)
                next_send_local = schedule.next_send.replace(tzinfo=pytz.UTC).astimezone(tz)

                await query.edit_message_text(
                    "✅ *Schedule Created Successfully!*\n\n"
                    f"Your news will be delivered at {schedule.time} ({schedule.timezone}).\n\n"
                    f"📅 Next delivery: {next_send_local.strftime('%A, %B %d at %I:%M %p')}\n\n"
                    "Use /schedule to view or manage your schedules.",
                    parse_mode='Markdown'
                )

                # Register the job
                from news_tracker.jobs.scheduled_delivery import ScheduledDelivery
                delivery = ScheduledDelivery(self.config, context.application.job_queue)
                delivery.schedule_job(schedule)

                return ConversationHandler.END
            else:
                await query.edit_message_text(
                    "❌ Failed to create schedule. Please try again later."
                )
                return ConversationHandler.END

        elif data == "conf_back":
            return await self._show_frequency_selection(update, context)
        elif data == "conf_cancel":
            self.temp_schedules.pop(user.id, None)
            await query.edit_message_text("❌ Cancelled.")
            return ConversationHandler.END

        return CONFIRM_SCHEDULE
    async def _view_schedules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View user's schedules"""
        user = update.effective_user

        schedules = self.schedule_manager.get_user_schedules(user.id, active_only=False)

        if not schedules:
            await update.callback_query.edit_message_text(
                "📋 You don't have any schedules yet.\n\n"
                "Use /schedule to create one!"
            )
            return ConversationHandler.END

        keyboard = []

        # Get all sources once (outside the loop for efficiency)
        all_sources = self.news_service.database.get_all_sources()

        for schedule in schedules:
            # Get source names
            source_names = [
                s['name'] for s in all_sources if s['search_id'] in schedule.sources
            ]

            status_icon = "✅" if schedule.is_active else "❌"
            button_text = f"{status_icon} {', '.join(source_names[:2])} - {schedule.time}"

            keyboard.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"{SCHEDULE_PREFIX}detail_{schedule.schedule_id}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("⬅️ Back", callback_data=f"{SCHEDULE_PREFIX}back"),
            InlineKeyboardButton("❌ Close", callback_data=f"{SCHEDULE_PREFIX}close")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            f"📋 *Your Schedules* ({len(schedules)}/5)\n\n"
            "Tap a schedule to view details or manage it."
        )

        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        return VIEW_SCHEDULES

    async def handle_view_schedules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle schedule viewing"""
        query = update.callback_query
        await query.answer()

        data = query.data.replace(SCHEDULE_PREFIX, "")

        if data == "back":
            return await self._show_schedule_menu(update, context)
        elif data == "close":
            await query.edit_message_text("✅ Closed.")
            return ConversationHandler.END
        elif data.startswith("detail_"):
            schedule_id = data.replace("detail_", "")
            return await self._show_schedule_detail(update, context, schedule_id)

        return VIEW_SCHEDULES

    async def _show_schedule_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, schedule_id: str):
        """Show detailed view of a schedule"""
        schedule = self.schedule_manager.get_schedule_by_id(schedule_id)

        if not schedule:
            await update.callback_query.edit_message_text(
                "❌ Schedule not found."
            )
            return ConversationHandler.END

        # Get source names from database
        all_sources = self.news_service.database.get_all_sources()
        source_names = [
            s['name'] for s in all_sources if s['search_id'] in schedule.sources
        ]

        # Format display
        format_display = {
            'text': '📰 Text Summary',
            'audio': '🔊 Audio Summary',
            'both': '📰🔊 Both'
        }

        frequency_display = {
            'daily': '📅 Daily',
            'weekdays': '💼 Weekdays',
            'weekends': '🏖️ Weekends'
        }

        # Get timezone display name
        timezones = ScheduleManager.get_available_timezones()
        tz_display = next(
            (name for tz_id, name in timezones if tz_id == schedule.timezone),
            schedule.timezone
        )

        # Format next send time
        import pytz
        tz = pytz.timezone(schedule.timezone)
        if schedule.next_send:
            next_send_local = schedule.next_send.replace(tzinfo=pytz.UTC).astimezone(tz)
            next_send_str = next_send_local.strftime('%A, %B %d at %I:%M %p')
        else:
            next_send_str = "Not scheduled"

        status = "✅ Active" if schedule.is_active else "❌ Inactive"

        text = (
            "📋 *Schedule Details*\n\n"
            f"• Sources: {', '.join(source_names)}\n"
            f"• Format: {format_display[schedule.format]}\n"
            f"• Time: {schedule.time}\n"
            f"• Timezone: {tz_display}\n"
            f"• Frequency: {frequency_display[schedule.frequency]}\n"
            f"• Status: {status}\n"
            f"• Next delivery: {next_send_str}\n"
        )

        if schedule.last_sent:
            last_sent_local = schedule.last_sent.replace(tzinfo=pytz.UTC).astimezone(tz)
            text += f"• Last sent: {last_sent_local.strftime('%B %d at %I:%M %p')}\n"

        keyboard = []

        # Toggle active/inactive
        if schedule.is_active:
            keyboard.append([
                InlineKeyboardButton(
                    "⏸️ Pause Schedule",
                    callback_data=f"{SCHEDULE_PREFIX}toggle_{schedule_id}_false"
                )
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(
                    "▶️ Resume Schedule",
                    callback_data=f"{SCHEDULE_PREFIX}toggle_{schedule_id}_true"
                )
            ])

        keyboard.append([
            InlineKeyboardButton(
                "🗑️ Delete Schedule",
                callback_data=f"{SCHEDULE_PREFIX}delete_{schedule_id}"
            )
        ])

        keyboard.append([
            InlineKeyboardButton("⬅️ Back to List", callback_data=f"{SCHEDULE_PREFIX}view")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        return VIEW_SCHEDULES

    async def handle_schedule_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle schedule actions (toggle, delete)"""
        query = update.callback_query
        await query.answer()

        data = query.data.replace(SCHEDULE_PREFIX, "")

        if data.startswith("toggle_"):
            parts = data.split("_")
            schedule_id = parts[1]
            is_active = parts[2] == "true"

            if self.schedule_manager.toggle_schedule(schedule_id, is_active):
                status = "resumed" if is_active else "paused"
                await query.answer(f"Schedule {status}!", show_alert=True)

                # Refresh the detail view
                return await self._show_schedule_detail(update, context, schedule_id)
            else:
                await query.answer("Failed to update schedule.", show_alert=True)
                return VIEW_SCHEDULES

        elif data.startswith("delete_"):
            schedule_id = data.replace("delete_", "")

            # Confirm deletion
            keyboard = [
                [
                    InlineKeyboardButton("✅ Yes, Delete", callback_data=f"{SCHEDULE_PREFIX}confirm_delete_{schedule_id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"{SCHEDULE_PREFIX}detail_{schedule_id}")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "⚠️ *Confirm Deletion*\n\n"
                "Are you sure you want to delete this schedule?\n"
                "This action cannot be undone.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            return VIEW_SCHEDULES

        elif data.startswith("confirm_delete_"):
            schedule_id = data.replace("confirm_delete_", "")

            if self.schedule_manager.delete_schedule(schedule_id):
                await query.edit_message_text(
                    "✅ Schedule deleted successfully!\n\n"
                    "Use /schedule to create a new one."
                )
                return ConversationHandler.END
            else:
                await query.answer("Failed to delete schedule.", show_alert=True)
                return VIEW_SCHEDULES

        return VIEW_SCHEDULES

    def get_conversation_handler(self) -> ConversationHandler:
        """
        Get the conversation handler for scheduling

        Returns:
            ConversationHandler configured for schedule management
        """
        return ConversationHandler(
            entry_points=[CommandHandler('schedule', self.schedule_command)],
            states={
                SCHEDULE_MENU: [
                    CallbackQueryHandler(self.handle_schedule_menu, pattern=f"^{SCHEDULE_PREFIX}")
                ],
                SELECT_SOURCES: [
                    CallbackQueryHandler(self.handle_source_selection, pattern=f"^{SOURCE_PREFIX}")
                ],
                SELECT_FORMAT: [
                    CallbackQueryHandler(self.handle_format_selection, pattern=f"^{FORMAT_PREFIX}")
                ],
                SELECT_TIME_PRESET: [
                    CallbackQueryHandler(self.handle_time_selection, pattern=f"^{TIME_PREFIX}")
                ],
                SELECT_CUSTOM_TIME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_custom_time)
                ],
                SELECT_TIMEZONE: [
                    CallbackQueryHandler(self.handle_timezone_selection, pattern=f"^{TZ_PREFIX}")
                ],
                SELECT_FREQUENCY: [
                    CallbackQueryHandler(self.handle_frequency_selection, pattern=f"^{FREQ_PREFIX}")
                ],
                CONFIRM_SCHEDULE: [
                    CallbackQueryHandler(self.handle_confirmation, pattern=f"^{SCHEDULE_PREFIX}")
                ],
                VIEW_SCHEDULES: [
                    CallbackQueryHandler(self.handle_view_schedules, pattern=f"^{SCHEDULE_PREFIX}(view|back|close|detail_)"),
                    CallbackQueryHandler(self.handle_schedule_action, pattern=f"^{SCHEDULE_PREFIX}(toggle_|delete_|confirm_delete_)")
                ],
            },
            fallbacks=[
                CommandHandler('cancel', lambda u, c: ConversationHandler.END)
            ],
            name="schedule_conversation",
            persistent=False
        )

