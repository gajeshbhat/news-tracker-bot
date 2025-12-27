"""
Schedule Manager for News Tracker Bot

Handles user schedules for automated news delivery.
"""

import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
import pytz


@dataclass
class Schedule:
    """User schedule data structure"""
    user_id: int
    username: Optional[str] = None
    schedule_name: Optional[str] = None
    sources: List[str] = None  # Max 2 sources
    format: str = "text"  # "text", "audio", "both"
    time: str = "08:00"  # HH:MM in user's timezone
    timezone: str = "UTC"  # User's timezone
    frequency: str = "daily"  # "daily", "weekdays", "weekends"
    is_active: bool = True
    created_at: datetime = None
    last_sent: Optional[datetime] = None
    next_send: Optional[datetime] = None
    schedule_id: Optional[str] = None  # MongoDB _id as string
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.sources is None:
            self.sources = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage"""
        data = asdict(self)
        # Remove schedule_id as it's stored as _id in MongoDB
        data.pop('schedule_id', None)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Schedule':
        """Create from MongoDB document"""
        # Convert MongoDB _id to schedule_id string
        clean_data = {k: v for k, v in data.items() if k != '_id'}
        if '_id' in data:
            clean_data['schedule_id'] = str(data['_id'])
        return cls(**clean_data)


class ScheduleManager:
    """Manages user schedules for automated news delivery"""
    
    def __init__(self, mongodb_uri: str = "mongodb://localhost:27017/"):
        """
        Initialize the schedule manager
        
        Args:
            mongodb_uri: MongoDB connection URI
        """
        self.client = MongoClient(mongodb_uri)
        self.db = self.client.news_tracker
        self.schedules_collection = self.db.user_schedules
        self.logger = logging.getLogger(__name__)
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for efficient queries"""
        try:
            # Index on user_id for fast user lookups
            self.schedules_collection.create_index([("user_id", ASCENDING)])
            
            # Index on is_active for filtering active schedules
            self.schedules_collection.create_index([("is_active", ASCENDING)])
            
            # Index on next_send for job queue processing
            self.schedules_collection.create_index([("next_send", ASCENDING)])
            
            # Compound index for active schedules by user
            self.schedules_collection.create_index([
                ("user_id", ASCENDING),
                ("is_active", ASCENDING)
            ])
            
            self.logger.info("Schedule indexes created successfully")
        except Exception as e:
            self.logger.error(f"Error creating indexes: {e}")
    
    def create_schedule(
        self,
        user_id: int,
        sources: List[str],
        format: str,
        time_str: str,
        timezone: str,
        frequency: str,
        username: Optional[str] = None,
        schedule_name: Optional[str] = None
    ) -> Optional[Schedule]:
        """
        Create a new schedule for a user
        
        Args:
            user_id: Telegram user ID
            sources: List of news source IDs (max 2)
            format: Delivery format ("text", "audio", "both")
            time_str: Time in HH:MM format
            timezone: User's timezone (e.g., "America/New_York")
            frequency: Delivery frequency ("daily", "weekdays", "weekends")
            username: Telegram username (optional)
            schedule_name: Custom name for schedule (optional)
        
        Returns:
            Schedule object if successful, None otherwise
        """
        try:
            # Validate sources limit
            if len(sources) > 2:
                self.logger.error(f"Too many sources: {len(sources)} (max 2)")
                return None
            
            # Validate format
            if format not in ["text", "audio", "both"]:
                self.logger.error(f"Invalid format: {format}")
                return None
            
            # Validate frequency
            if frequency not in ["daily", "weekdays", "weekends"]:
                self.logger.error(f"Invalid frequency: {frequency}")
                return None
            
            # Calculate next send time
            next_send = self._calculate_next_send(time_str, timezone, frequency)
            
            # Create schedule object
            schedule = Schedule(
                user_id=user_id,
                username=username,
                schedule_name=schedule_name,
                sources=sources,
                format=format,
                time=time_str,
                timezone=timezone,
                frequency=frequency,
                next_send=next_send
            )
            
            # Insert into database
            result = self.schedules_collection.insert_one(schedule.to_dict())
            schedule.schedule_id = str(result.inserted_id)
            
            self.logger.info(f"Created schedule {schedule.schedule_id} for user {user_id}")
            return schedule
            
        except Exception as e:
            self.logger.error(f"Error creating schedule: {e}")
            return None
    
    def get_user_schedules(self, user_id: int, active_only: bool = True) -> List[Schedule]:
        """
        Get all schedules for a user
        
        Args:
            user_id: Telegram user ID
            active_only: Only return active schedules
        
        Returns:
            List of Schedule objects
        """
        try:
            query = {'user_id': user_id}
            if active_only:
                query['is_active'] = True
            
            schedules_data = self.schedules_collection.find(query)
            return [Schedule.from_dict(data) for data in schedules_data]
            
        except Exception as e:
            self.logger.error(f"Error getting user schedules: {e}")
            return []
    
    def get_schedule_by_id(self, schedule_id: str) -> Optional[Schedule]:
        """
        Get a schedule by its ID
        
        Args:
            schedule_id: MongoDB ObjectId as string
        
        Returns:
            Schedule object if found, None otherwise
        """
        try:
            from bson import ObjectId
            schedule_data = self.schedules_collection.find_one({'_id': ObjectId(schedule_id)})
            
            if schedule_data:
                return Schedule.from_dict(schedule_data)
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting schedule by ID: {e}")
            return None
    
    def update_schedule(
        self,
        schedule_id: str,
        sources: Optional[List[str]] = None,
        format: Optional[str] = None,
        time_str: Optional[str] = None,
        timezone: Optional[str] = None,
        frequency: Optional[str] = None,
        schedule_name: Optional[str] = None
    ) -> bool:
        """
        Update an existing schedule
        
        Args:
            schedule_id: MongoDB ObjectId as string
            sources: New sources list (optional)
            format: New format (optional)
            time_str: New time (optional)
            timezone: New timezone (optional)
            frequency: New frequency (optional)
            schedule_name: New name (optional)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            from bson import ObjectId
            
            # Build update dict
            update_data = {}
            
            if sources is not None:
                if len(sources) > 2:
                    self.logger.error(f"Too many sources: {len(sources)} (max 2)")
                    return False
                update_data['sources'] = sources
            
            if format is not None:
                if format not in ["text", "audio", "both"]:
                    self.logger.error(f"Invalid format: {format}")
                    return False
                update_data['format'] = format
            
            if time_str is not None:
                update_data['time'] = time_str
            
            if timezone is not None:
                update_data['timezone'] = timezone
            
            if frequency is not None:
                if frequency not in ["daily", "weekdays", "weekends"]:
                    self.logger.error(f"Invalid frequency: {frequency}")
                    return False
                update_data['frequency'] = frequency
            
            if schedule_name is not None:
                update_data['schedule_name'] = schedule_name
            
            # Recalculate next_send if time/timezone/frequency changed
            if any(k in update_data for k in ['time', 'timezone', 'frequency']):
                schedule = self.get_schedule_by_id(schedule_id)
                if schedule:
                    new_time = update_data.get('time', schedule.time)
                    new_tz = update_data.get('timezone', schedule.timezone)
                    new_freq = update_data.get('frequency', schedule.frequency)
                    update_data['next_send'] = self._calculate_next_send(new_time, new_tz, new_freq)
            
            if not update_data:
                return True  # Nothing to update
            
            # Update in database
            result = self.schedules_collection.update_one(
                {'_id': ObjectId(schedule_id)},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                self.logger.info(f"Updated schedule {schedule_id}")
                return True
            else:
                self.logger.warning(f"No changes made to schedule {schedule_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating schedule: {e}")
            return False

    def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule

        Args:
            schedule_id: MongoDB ObjectId as string

        Returns:
            True if successful, False otherwise
        """
        try:
            from bson import ObjectId
            result = self.schedules_collection.delete_one({'_id': ObjectId(schedule_id)})

            if result.deleted_count > 0:
                self.logger.info(f"Deleted schedule {schedule_id}")
                return True
            else:
                self.logger.warning(f"Schedule not found: {schedule_id}")
                return False

        except Exception as e:
            self.logger.error(f"Error deleting schedule: {e}")
            return False

    def toggle_schedule(self, schedule_id: str, is_active: bool) -> bool:
        """
        Enable or disable a schedule

        Args:
            schedule_id: MongoDB ObjectId as string
            is_active: True to enable, False to disable

        Returns:
            True if successful, False otherwise
        """
        try:
            from bson import ObjectId
            result = self.schedules_collection.update_one(
                {'_id': ObjectId(schedule_id)},
                {'$set': {'is_active': is_active}}
            )

            if result.modified_count > 0:
                status = "enabled" if is_active else "disabled"
                self.logger.info(f"Schedule {schedule_id} {status}")
                return True
            else:
                self.logger.warning(f"Failed to toggle schedule {schedule_id}")
                return False

        except Exception as e:
            self.logger.error(f"Error toggling schedule: {e}")
            return False

    def get_active_schedules(self) -> List[Schedule]:
        """
        Get all active schedules across all users

        Returns:
            List of active Schedule objects
        """
        try:
            schedules_data = self.schedules_collection.find({'is_active': True})
            return [Schedule.from_dict(data) for data in schedules_data]

        except Exception as e:
            self.logger.error(f"Error getting active schedules: {e}")
            return []

    def get_due_schedules(self, current_time: Optional[datetime] = None) -> List[Schedule]:
        """
        Get schedules that are due for delivery

        Args:
            current_time: Current time (defaults to now in UTC)

        Returns:
            List of Schedule objects due for delivery
        """
        try:
            if current_time is None:
                current_time = datetime.utcnow()

            schedules_data = self.schedules_collection.find({
                'is_active': True,
                'next_send': {'$lte': current_time}
            })

            return [Schedule.from_dict(data) for data in schedules_data]

        except Exception as e:
            self.logger.error(f"Error getting due schedules: {e}")
            return []

    def mark_as_sent(self, schedule_id: str) -> bool:
        """
        Mark a schedule as sent and calculate next send time

        Args:
            schedule_id: MongoDB ObjectId as string

        Returns:
            True if successful, False otherwise
        """
        try:
            from bson import ObjectId

            # Get current schedule
            schedule = self.get_schedule_by_id(schedule_id)
            if not schedule:
                return False

            # Calculate next send time
            next_send = self._calculate_next_send(
                schedule.time,
                schedule.timezone,
                schedule.frequency,
                from_time=datetime.utcnow()
            )

            # Update database
            result = self.schedules_collection.update_one(
                {'_id': ObjectId(schedule_id)},
                {
                    '$set': {
                        'last_sent': datetime.utcnow(),
                        'next_send': next_send
                    }
                }
            )

            if result.modified_count > 0:
                self.logger.info(f"Marked schedule {schedule_id} as sent, next: {next_send}")
                return True
            else:
                self.logger.warning(f"Failed to mark schedule {schedule_id} as sent")
                return False

        except Exception as e:
            self.logger.error(f"Error marking schedule as sent: {e}")
            return False

    def count_user_schedules(self, user_id: int, active_only: bool = True) -> int:
        """
        Count schedules for a user

        Args:
            user_id: Telegram user ID
            active_only: Only count active schedules

        Returns:
            Number of schedules
        """
        try:
            query = {'user_id': user_id}
            if active_only:
                query['is_active'] = True

            return self.schedules_collection.count_documents(query)

        except Exception as e:
            self.logger.error(f"Error counting user schedules: {e}")
            return 0

    def _calculate_next_send(
        self,
        time_str: str,
        timezone: str,
        frequency: str,
        from_time: Optional[datetime] = None
    ) -> datetime:
        """
        Calculate the next send time for a schedule

        Args:
            time_str: Time in HH:MM format
            timezone: Timezone string (e.g., "America/New_York")
            frequency: "daily", "weekdays", or "weekends"
            from_time: Calculate from this time (defaults to now)

        Returns:
            Next send time in UTC
        """
        try:
            if from_time is None:
                from_time = datetime.utcnow()

            # Parse time
            hour, minute = map(int, time_str.split(':'))

            # Get timezone
            tz = pytz.timezone(timezone)

            # Get current time in user's timezone
            current_local = from_time.replace(tzinfo=pytz.UTC).astimezone(tz)

            # Create next send time for today
            next_local = current_local.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # If time has passed today, start from tomorrow
            if next_local <= current_local:
                next_local += timedelta(days=1)

            # Adjust for frequency
            if frequency == "weekdays":
                # Monday = 0, Sunday = 6
                while next_local.weekday() >= 5:  # Saturday or Sunday
                    next_local += timedelta(days=1)
            elif frequency == "weekends":
                # Move to next Saturday or Sunday
                while next_local.weekday() < 5:  # Not weekend
                    next_local += timedelta(days=1)

            # Convert back to UTC
            next_utc = next_local.astimezone(pytz.UTC).replace(tzinfo=None)

            return next_utc

        except Exception as e:
            self.logger.error(f"Error calculating next send time: {e}")
            # Default to 24 hours from now
            return (from_time or datetime.utcnow()) + timedelta(days=1)

    @staticmethod
    def get_available_timezones() -> List[Tuple[str, str]]:
        """
        Get list of common timezones for user selection

        Returns:
            List of (timezone_id, display_name) tuples, sorted alphabetically with UTC first
        """
        # Common timezones with user-friendly names
        common_timezones = [
            ("UTC", "🌍 UTC (Coordinated Universal Time)"),
            ("America/New_York", "🇺🇸 Eastern Time (US & Canada)"),
            ("America/Chicago", "🇺🇸 Central Time (US & Canada)"),
            ("America/Denver", "🇺🇸 Mountain Time (US & Canada)"),
            ("America/Los_Angeles", "🇺🇸 Pacific Time (US & Canada)"),
            ("America/Anchorage", "🇺🇸 Alaska"),
            ("Pacific/Honolulu", "🇺🇸 Hawaii"),
            ("Europe/London", "🇬🇧 London (GMT/BST)"),
            ("Europe/Paris", "🇫🇷 Paris (CET/CEST)"),
            ("Europe/Berlin", "🇩🇪 Berlin (CET/CEST)"),
            ("Europe/Rome", "🇮🇹 Rome (CET/CEST)"),
            ("Europe/Madrid", "🇪🇸 Madrid (CET/CEST)"),
            ("Europe/Moscow", "🇷🇺 Moscow (MSK)"),
            ("Asia/Dubai", "🇦🇪 Dubai (GST)"),
            ("Asia/Kolkata", "🇮🇳 India (IST)"),
            ("Asia/Shanghai", "🇨🇳 China (CST)"),
            ("Asia/Hong_Kong", "🇭🇰 Hong Kong (HKT)"),
            ("Asia/Tokyo", "🇯🇵 Tokyo (JST)"),
            ("Asia/Seoul", "🇰🇷 Seoul (KST)"),
            ("Asia/Singapore", "🇸🇬 Singapore (SGT)"),
            ("Australia/Sydney", "🇦🇺 Sydney (AEDT/AEST)"),
            ("Australia/Melbourne", "🇦🇺 Melbourne (AEDT/AEST)"),
            ("Australia/Perth", "🇦🇺 Perth (AWST)"),
            ("Pacific/Auckland", "🇳🇿 Auckland (NZDT/NZST)"),
            ("America/Sao_Paulo", "🇧🇷 São Paulo (BRT)"),
            ("America/Mexico_City", "🇲🇽 Mexico City (CST)"),
            ("America/Toronto", "🇨🇦 Toronto (EST/EDT)"),
            ("America/Vancouver", "🇨🇦 Vancouver (PST/PDT)"),
        ]

        # Sort alphabetically by display name, but keep UTC first
        utc = common_timezones[0]
        others = sorted(common_timezones[1:], key=lambda x: x[1])

        return [utc] + others

