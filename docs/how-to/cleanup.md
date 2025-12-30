# Cleanup Setup

The cleanup script removes old audio files, articles, and inactive schedules to prevent disk space issues.

## What Gets Cleaned

- Audio files older than 24 hours
- Article collections older than 7 days
- Inactive schedules older than 90 days

## Manual Cleanup

View current storage:
```bash
pipenv run python -m news_tracker.scripts.cleanup --stats-only
```

Run cleanup with defaults:
```bash
pipenv run python -m news_tracker.scripts.cleanup
```

Custom retention periods:
```bash
pipenv run python -m news_tracker.scripts.cleanup \
    --audio-age 48 \
    --articles-age 14 \
    --schedules-age 180
```

## Automated Cleanup

The setup script automatically configures a cron job that runs daily at 3 AM.

### Manual Cron Setup

If you didn't use the setup script, add this to crontab:

```bash
crontab -e
```

Add this line (replace `/path/to/project` with your actual path):
```
0 3 * * * cd /path/to/project && $HOME/.local/bin/pipenv run python -m news_tracker.scripts.cleanup >> /path/to/project/logs/cleanup.log 2>&1
```

### Verify Cron Job

Check if cleanup is scheduled:
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

