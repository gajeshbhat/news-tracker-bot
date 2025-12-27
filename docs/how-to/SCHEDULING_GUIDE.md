# 📅 Scheduling Guide - News Tracker Bot

## Overview

The News Tracker Bot now supports **automated scheduled news delivery**! Users can set up custom schedules to receive news summaries at specific times in their preferred timezone.

## Features

### ✨ Key Capabilities

- **📅 Flexible Scheduling**: Daily, weekdays, or weekends delivery
- **🌍 Timezone Support**: 27+ common timezones with UTC at the top
- **📰 Multi-Source**: Select up to 2 news sources per schedule
- **🎯 Format Options**: Text, Audio, or Both in the same message
- **⏰ Time Presets**: Morning, Noon, Evening, Night, or custom time
- **📊 Multiple Schedules**: Up to 5 active schedules per user
- **⏸️ Pause/Resume**: Toggle schedules on/off without deleting
- **🔔 Smart Delivery**: Respects product key rate limits

## User Guide

### Creating a Schedule

1. **Start the process**:
   ```
   /schedule
   ```

2. **Select "Create New Schedule"**

3. **Choose News Sources** (up to 2):
   - Browse through paginated list of 127+ sources
   - Select/deselect by tapping source buttons
   - Green checkmark (✅) indicates selected sources

4. **Select Format**:
   - 📰 Text Summary - Articles with clickable links
   - 🔊 Audio Summary - AI-generated voice summary
   - 📰🔊 Both - Text and audio in same delivery

5. **Choose Time**:
   - **Presets**:
     - 🌅 Morning (8:00 AM)
     - ☀️ Noon (12:00 PM)
     - 🌆 Evening (6:00 PM)
     - 🌙 Night (10:00 PM)
   - **Custom**: Enter time in HH:MM format (e.g., 14:30)

6. **Select Timezone**:
   - UTC is always at the top
   - 27+ common timezones sorted alphabetically
   - Paginated for easy browsing

7. **Choose Frequency**:
   - 📅 Daily - Every day
   - 💼 Weekdays - Monday through Friday
   - 🏖️ Weekends - Saturday and Sunday

8. **Confirm**:
   - Review your schedule summary
   - Tap "✅ Create Schedule" to activate

### Managing Schedules

#### View Schedules
```
/schedule → View My Schedules
```

Shows all your schedules with:
- Status (✅ Active / ❌ Inactive)
- Source names
- Delivery time

#### Schedule Details

Tap any schedule to see:
- Sources
- Format (Text/Audio/Both)
- Time and timezone
- Frequency
- Status
- Next delivery time
- Last sent time

#### Pause/Resume Schedule

From schedule details:
- **⏸️ Pause Schedule** - Temporarily stop deliveries
- **▶️ Resume Schedule** - Reactivate deliveries

#### Delete Schedule

From schedule details:
- Tap **🗑️ Delete Schedule**
- Confirm deletion
- Schedule is permanently removed

### Rate Limits

Scheduled deliveries count toward your daily product key limit:

- If limit is reached, you'll receive a notification
- Delivery will resume the next day
- Contact administrator to increase your limit

## Technical Details

### Database Schema

```python
{
    "user_id": 123456789,
    "username": "johndoe",
    "schedule_name": "Morning News",
    "sources": ["bbc-news", "cnn"],
    "format": "both",  # "text", "audio", or "both"
    "time": "08:00",  # HH:MM in user's timezone
    "timezone": "America/New_York",
    "frequency": "weekdays",  # "daily", "weekdays", or "weekends"
    "is_active": true,
    "created_at": "2025-12-27T10:00:00Z",
    "last_sent": "2025-12-27T13:00:00Z",
    "next_send": "2025-12-28T13:00:00Z"
}
```

### Supported Timezones

- UTC (always first)
- America/New_York (EST/EDT)
- America/Chicago (CST/CDT)
- America/Denver (MST/MDT)
- America/Los_Angeles (PST/PDT)
- Europe/London (GMT/BST)
- Europe/Paris (CET/CEST)
- Europe/Berlin (CET/CEST)
- Europe/Moscow (MSK)
- Asia/Dubai (GST)
- Asia/Kolkata (IST)
- Asia/Shanghai (CST)
- Asia/Tokyo (JST)
- Asia/Seoul (KST)
- Asia/Singapore (SGT)
- Asia/Hong_Kong (HKT)
- Australia/Sydney (AEDT/AEST)
- Australia/Melbourne (AEDT/AEST)
- Australia/Perth (AWST)
- Pacific/Auckland (NZDT/NZST)
- Pacific/Fiji (FJT)
- Africa/Cairo (EET)
- Africa/Johannesburg (SAST)
- Africa/Lagos (WAT)
- America/Sao_Paulo (BRT)
- America/Mexico_City (CST/CDT)
- America/Toronto (EST/EDT)

### Frequency Calculation

**Daily**: Delivers every day at the specified time

**Weekdays**: Delivers Monday-Friday
- If today is Friday and next delivery would be Saturday, schedules for Monday

**Weekends**: Delivers Saturday-Sunday
- If today is Sunday and next delivery would be Monday, schedules for next Saturday

### Job Queue System

- Uses `python-telegram-bot` JobQueue
- Jobs are persistent across bot restarts
- All active schedules are loaded on bot startup
- Failed deliveries are retried in 1 hour
- Successful deliveries automatically reschedule for next occurrence

## Admin Guide

### CLI Commands

```bash
# View all schedules (admin only - requires database access)
mongo news_tracker --eval "db.user_schedules.find().pretty()"

# Count active schedules
mongo news_tracker --eval "db.user_schedules.countDocuments({is_active: true})"

# Find schedules for a specific user
mongo news_tracker --eval "db.user_schedules.find({user_id: 123456789}).pretty()"

# Delete all schedules for a user
mongo news_tracker --eval "db.user_schedules.deleteMany({user_id: 123456789})"
```

### Monitoring

Check logs for scheduled delivery activity:

```bash
# Watch for schedule-related logs
tail -f logs/news_tracker.log | grep -i schedule

# Check for delivery errors
tail -f logs/errors.log | grep -i schedule
```

### Troubleshooting

**Schedules not delivering**:
1. Check bot is running: `ps aux | grep ntb`
2. Check MongoDB is running: `docker ps | grep mongo`
3. Check logs for errors: `tail -f logs/news_tracker.log`
4. Verify schedule is active: Check database

**Wrong delivery time**:
1. Verify timezone is correct in schedule
2. Check server time: `date`
3. Verify pytz is installed: `pipenv run python -c "import pytz; print(pytz.VERSION)"`

**Rate limit issues**:
1. Check user's product key: `pipenv run ntb keys info --user-id <USER_ID>`
2. Increase limit if needed: Update product key in database
3. Check daily usage: Review logs

## Best Practices

### For Users

1. **Start with one schedule** - Test before creating multiple
2. **Use meaningful source combinations** - Related topics work best
3. **Consider timezone carefully** - Double-check your local time
4. **Pause instead of delete** - If you need a temporary break
5. **Monitor your rate limit** - Scheduled deliveries count toward daily limit

### For Administrators

1. **Set reasonable rate limits** - Consider scheduled + manual requests
2. **Monitor database size** - Old schedules can accumulate
3. **Regular backups** - Schedule data is valuable to users
4. **Log rotation** - Scheduled deliveries generate logs
5. **Performance monitoring** - Many schedules at same time can spike load

## Examples

### Example 1: Morning Tech News

- **Sources**: TechCrunch, The Verge
- **Format**: Text
- **Time**: 8:00 AM
- **Timezone**: America/New_York
- **Frequency**: Weekdays

**Result**: Receive tech news every weekday morning at 8 AM EST

### Example 2: Evening World News

- **Sources**: BBC News, CNN
- **Format**: Both (Text + Audio)
- **Time**: 6:00 PM
- **Timezone**: Europe/London
- **Frequency**: Daily

**Result**: Receive world news every evening at 6 PM GMT with both text and audio

### Example 3: Weekend Sports

- **Sources**: ESPN, BBC Sport
- **Format**: Audio
- **Time**: 10:00 AM
- **Timezone**: America/Los_Angeles
- **Frequency**: Weekends

**Result**: Receive sports news audio summary on Saturday and Sunday mornings at 10 AM PST

## Limitations

- **Max 5 schedules per user** - Prevents abuse and ensures fair usage
- **Max 2 sources per schedule** - Keeps deliveries concise and relevant
- **No catch-up for missed deliveries** - If bot is down, missed deliveries are skipped
- **Rate limits apply** - Scheduled deliveries count toward daily limit
- **English audio only** - Currently audio summaries are in English (text supports all languages)

## Future Enhancements

Potential features for future versions:

- [ ] Edit existing schedules
- [ ] Schedule templates
- [ ] Multi-language audio support
- [ ] Custom schedule names
- [ ] Delivery history
- [ ] Schedule sharing
- [ ] Smart scheduling (avoid duplicate content)
- [ ] Notification preferences
- [ ] Catch-up mode for missed deliveries

---

**Need help?** Contact the administrator or use `/help` in the bot.

