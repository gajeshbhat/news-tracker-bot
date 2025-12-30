# Deployment Files

This directory contains deployment configuration files and scripts for News Tracker Bot.

## Directory Structure

```
deployment/
├── gentoo-pi/
│   └── setup.sh              # Automated setup script for Gentoo Linux
├── systemd/
│   └── news-tracker-bot.service  # systemd service template
└── cron/
    └── news-tracker-cleanup  # Cron job template for cleanup
```

## Quick Deployment (Gentoo)

```bash
cd news-tracker-bot
chmod +x deployment/gentoo-pi/setup.sh
./deployment/gentoo-pi/setup.sh
```

This will:
- Install system dependencies (FFmpeg, Docker, Git, Vim, Cronie)
- Create virtual environment and install Python dependencies
- Setup MongoDB container
- Configure environment variables
- Initialize database
- Create systemd service
- Setup log rotation
- Configure automated cleanup

## Manual Deployment

### 1. systemd Service

Copy and customize the service file:

```bash
# Edit the template with your paths
cp deployment/systemd/news-tracker-bot.service /tmp/news-tracker-bot.service
vim /tmp/news-tracker-bot.service

# Replace:
# - YOUR_USERNAME with your username
# - /path/to/news-tracker-bot with actual path

# Install the service
sudo cp /tmp/news-tracker-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable news-tracker-bot
sudo systemctl start news-tracker-bot
```

### 2. Cleanup Cron Job

Option A: System cron (recommended):

```bash
# Edit the template with your paths
cp deployment/cron/news-tracker-cleanup /tmp/news-tracker-cleanup
vim /tmp/news-tracker-cleanup

# Replace:
# - YOUR_USERNAME with your username
# - /path/to/news-tracker-bot with actual path (3 occurrences)

# Install the cron job
sudo cp /tmp/news-tracker-cleanup /etc/cron.d/
sudo systemctl restart cronie  # or cron on Ubuntu/Debian
```

Option B: User crontab:

```bash
crontab -e
```

Add (replace paths):
```
0 3 * * * cd /path/to/news-tracker-bot && /path/to/news-tracker-bot/venv/bin/python -m news_tracker.scripts.cleanup >> /path/to/news-tracker-bot/logs/cleanup.log 2>&1
```

## Verification

Check service status:
```bash
sudo systemctl status news-tracker-bot
```

View logs:
```bash
journalctl -u news-tracker-bot -f
```

Check cron job:
```bash
cat /etc/cron.d/news-tracker-cleanup
# or
crontab -l
```

Test cleanup manually:
```bash
source venv/bin/activate
python -m news_tracker.scripts.cleanup --stats-only
```

## Troubleshooting

Service won't start:
```bash
journalctl -u news-tracker-bot -n 50
sudo systemctl status news-tracker-bot
```

Cron not running:
```bash
sudo systemctl status cronie  # or cron
tail -f logs/cleanup.log
```

Permission issues:
```bash
# Ensure user is in docker group
groups
# If not, add and re-login:
sudo usermod -aG docker $USER
```

