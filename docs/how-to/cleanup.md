# Cleanup Setup

The cleanup script removes old audio files, articles, and inactive schedules to prevent disk space issues.

## What Gets Cleaned

- Audio files older than 24 hours
- Article collections older than 7 days
- Inactive schedules older than 90 days

## Manual Cleanup

Activate virtual environment first:
```bash
source venv/bin/activate
```

View current storage:
```bash
python -m news_tracker.scripts.cleanup --stats-only
```

Run cleanup with defaults:
```bash
python -m news_tracker.scripts.cleanup
```

Custom retention periods:
```bash
python -m news_tracker.scripts.cleanup \
    --audio-age 48 \
    --articles-age 14 \
    --schedules-age 180
```

## Automated Cleanup

The setup script automatically configures a cron job that runs daily at 3 AM.

### Manual Cron Setup

If you didn't use the setup script, you can set it up manually.

Option 1: System cron (recommended for Gentoo):
```bash
sudo tee /etc/cron.d/news-tracker-cleanup > /dev/null <<EOF
0 3 * * * yourusername cd /path/to/news-tracker-bot && /path/to/news-tracker-bot/venv/bin/python -m news_tracker.scripts.cleanup >> /path/to/news-tracker-bot/logs/cleanup.log 2>&1
EOF

sudo systemctl restart cronie  # or cron on Ubuntu/Debian
```

Option 2: User crontab:
```bash
crontab -e
```

Add this line (replace paths with your actual paths):
```
0 3 * * * cd /path/to/news-tracker-bot && /path/to/news-tracker-bot/venv/bin/python -m news_tracker.scripts.cleanup >> /path/to/news-tracker-bot/logs/cleanup.log 2>&1
```

### Verify Cron Job

Check system cron:
```bash
cat /etc/cron.d/news-tracker-cleanup
```

Or check user crontab:
```bash
crontab -l | grep cleanup
```

View cleanup logs:
```bash
tail -f logs/cleanup.log
```

## Storage Limits

With automatic cleanup enabled:

- Audio files: ~50-100 MB max
- Logs: ~85 MB max (auto-rotated)
- Database: ~1-10 MB (depends on users)
- Total: ~150-200 MB max

