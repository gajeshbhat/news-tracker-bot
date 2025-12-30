# Deployment

## Prerequisites

- Linux system (Gentoo, Ubuntu, Debian)
- Python 3.8+
- Docker
- Telegram Bot Token from @BotFather
- NewsAPI key from newsapi.org

## Gentoo Quick Setup

```bash
git clone <repository-url>
cd news-tracker-bot
chmod +x deployment/gentoo-pi/setup.sh
./deployment/gentoo-pi/setup.sh
```

Follow the prompts to configure your API keys.

After setup completes, log out and back in, then:

```bash
sudo systemctl start news-tracker-bot
sudo systemctl enable news-tracker-bot
```

## Manual Setup

### Install Dependencies

Gentoo:
```bash
sudo mkdir -p /etc/portage/package.use
echo "media-video/ffmpeg amr encode opus x264" | sudo tee -a /etc/portage/package.use/ffmpeg
sudo emerge media-video/ffmpeg app-containers/docker dev-vcs/git app-editors/vim sys-process/cronie
sudo systemctl enable --now docker
sudo systemctl enable --now cronie
sudo usermod -aG docker $USER
```

Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg docker.io git vim cron
sudo systemctl enable --now docker
sudo systemctl enable --now cron
sudo usermod -aG docker $USER
```

### Setup Project

```bash
git clone <repository-url>
cd news-tracker-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
vim .env  # Add TELEGRAM_BOT_TOKEN and NEWS_API_KEY
```

### Setup MongoDB

```bash
docker run -d \
    --name news-tracker-mongo \
    --restart unless-stopped \
    -p 27017:27017 \
    -v news-tracker-mongo-data:/data/db \
    mongo:7.0
```

### Initialize Database

```bash
ntb db init
```

### Test

```bash
ntb bot start
```

Press Ctrl+C to stop.

### Run in Background

Create systemd service:

```bash
# Get absolute paths
VENV_PATH="$(pwd)/venv"
WORK_DIR="$(pwd)"

sudo tee /etc/systemd/system/news-tracker-bot.service > /dev/null <<EOF
[Unit]
Description=News Tracker Bot
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORK_DIR
Environment="PATH=$VENV_PATH/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$VENV_PATH/bin/ntb bot start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable news-tracker-bot
sudo systemctl start news-tracker-bot
```

### Setup Log Rotation

```bash
sudo tee /etc/logrotate.d/news-tracker-bot > /dev/null <<EOF
$(pwd)/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $USER $USER
}
EOF
```

### Setup Automated Cleanup

See [cleanup guide](cleanup.md) for details.

Quick setup (Gentoo/systems with cron.d):
```bash
sudo tee /etc/cron.d/news-tracker-cleanup > /dev/null <<EOF
0 3 * * * $USER cd $(pwd) && $(pwd)/venv/bin/python -m news_tracker.scripts.cleanup >> $(pwd)/logs/cleanup.log 2>&1
EOF

sudo systemctl restart cronie  # or cron on Ubuntu/Debian
```

Alternative (user crontab):
```bash
crontab -e
```

Add this line:
```
0 3 * * * cd /path/to/news-tracker-bot && /path/to/news-tracker-bot/venv/bin/python -m news_tracker.scripts.cleanup >> /path/to/news-tracker-bot/logs/cleanup.log 2>&1
```

## Managing the Service

Start:
```bash
sudo systemctl start news-tracker-bot
```

Stop:
```bash
sudo systemctl stop news-tracker-bot
```

Restart:
```bash
sudo systemctl restart news-tracker-bot
```

Status:
```bash
sudo systemctl status news-tracker-bot
```

Logs:
```bash
journalctl -u news-tracker-bot -f
```

## Backup

MongoDB:
```bash
docker exec news-tracker-mongo mongodump --out=/data/db/backup
docker cp news-tracker-mongo:/data/db/backup ./mongodb-backup
```

Configuration:
```bash
tar -czf config-backup.tar.gz .env logs/
```

## Restore

MongoDB:
```bash
docker cp ./mongodb-backup news-tracker-mongo:/data/db/restore
docker exec news-tracker-mongo mongorestore /data/db/restore
```

Configuration:
```bash
tar -xzf config-backup.tar.gz
```

## Troubleshooting

Bot won't start:
```bash
journalctl -u news-tracker-bot -n 50
docker ps | grep mongo
cat .env
```

MongoDB issues:
```bash
docker ps | grep news-tracker-mongo
docker logs news-tracker-mongo
docker exec news-tracker-mongo mongosh --eval "db.adminCommand('ping')"
```

Permission issues:
```bash
groups  # Check if you're in docker group
# If not, log out and back in
```
