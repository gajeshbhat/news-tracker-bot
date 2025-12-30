# Storage

## What Gets Stored

### Audio Files

Location: `data/audio/`
Size: 200-900 KB per file
Lifecycle:
- Created for `/latest` command
- Overwritten on subsequent requests
- Scheduled deliveries use temp files (deleted after sending)

Growth:
- Max 127 files (one per source)
- ~64 MB maximum

Cleanup:
- Files older than 24 hours removed automatically
- Overwritten on re-request

### Log Files

Location: `logs/`

Files:
- `news_tracker.log` - Main log (10 MB max, 5 backups)
- `errors.log` - Errors only (5 MB max, 3 backups)
- `api_calls.log` - API tracking (5 MB max, 2 backups)
- `bot_interactions.log` - User interactions (5 MB max, 2 backups)

Total: ~85 MB max

Rotation: Automatic via RotatingFileHandler

### Database

Location: MongoDB container (`news-tracker-mongo`)

Collections:
- `users` - User data and preferences
- `product_keys` - License keys
- `schedules` - Delivery schedules
- `articles_{source_id}` - Cached articles per source

Size:
- Users: ~1 KB per user
- Product keys: ~500 bytes per key
- Schedules: ~2 KB per schedule
- Articles: ~5 KB per article, 100 articles per source

Growth:
- Users: Grows with user base
- Product keys: Grows with key generation
- Schedules: Grows with active schedules
- Articles: Refreshed on each request (no accumulation)

Cleanup:
- Article collections older than 7 days removed
- Inactive schedules older than 90 days removed
- Expired product keys deactivated

### Session Data

Location: In-memory (bot process)

Size: ~10 KB per active user
Lifecycle: 30-minute timeout
Cleanup: Automatic on timeout

## Total Storage

Typical usage:
- Audio: 10-50 MB
- Logs: 10-85 MB
- Database: 1-10 MB
- Total: 20-150 MB

Maximum (worst case):
- Audio: 64 MB
- Logs: 85 MB
- Database: 50 MB
- Total: ~200 MB

## Configuration

Environment variables:

```bash
AUDIO_DIR=data/audio          # Audio file location
LOG_DIR=logs                  # Log file location
MONGODB_URI=mongodb://localhost:27017  # Database connection
```

## Cleanup

See [cleanup guide](../how-to/cleanup.md) for automated cleanup setup.

Manual cleanup:
```bash
# View storage stats
pipenv run python -m news_tracker.scripts.cleanup --stats-only

# Run cleanup
pipenv run python -m news_tracker.scripts.cleanup
```

## Backup

MongoDB:
```bash
docker exec news-tracker-mongo mongodump --out=/data/db/backup
docker cp news-tracker-mongo:/data/db/backup ./mongodb-backup
```

Audio and logs:
```bash
tar -czf data-backup.tar.gz data/ logs/
```

## Restore

MongoDB:
```bash
docker cp ./mongodb-backup news-tracker-mongo:/data/db/restore
docker exec news-tracker-mongo mongorestore /data/db/restore
```

Audio and logs:
```bash
tar -xzf data-backup.tar.gz
```
