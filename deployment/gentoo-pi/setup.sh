#!/bin/bash
# Gentoo setup script for News Tracker Bot

set -e

echo "News Tracker Bot - Gentoo Setup"
echo ""

if [ "$EUID" -eq 0 ]; then
    echo "Error: Do not run as root"
    exit 1
fi

if [ ! -f /etc/gentoo-release ]; then
    echo "Error: This script is for Gentoo Linux"
    exit 1
fi

# Install system packages
echo "Installing system packages..."
sudo mkdir -p /etc/portage/package.use
echo "media-video/ffmpeg amr encode opus x264" | sudo tee -a /etc/portage/package.use/ffmpeg

sudo emerge --ask media-video/ffmpeg \
    app-containers/docker \
    app-containers/docker-compose \
    dev-vcs/git \
    app-editors/vim

echo "System packages installed"
echo ""

# Configure Docker
echo "Configuring Docker..."
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
echo "Docker configured (log out and back in for group changes)"
echo ""

# Install pipenv
echo "Installing pipenv..."
pip3 install --user pipenv
if ! grep -q '.local/bin' ~/.bashrc; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi
export PATH="$HOME/.local/bin:$PATH"
echo "pipenv installed"
echo ""

# Verify project directory
if [ ! -f "setup.py" ] || [ ! -d "news_tracker" ]; then
    echo "Error: Not in news-tracker-bot directory"
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pipenv install
echo ""

# Setup MongoDB
echo "Setting up MongoDB..."
if ! docker ps -a | grep -q news-tracker-mongo; then
    docker run -d \
        --name news-tracker-mongo \
        --restart unless-stopped \
        -p 27017:27017 \
        -v news-tracker-mongo-data:/data/db \
        mongo:7.0
    sleep 5
    echo "MongoDB started"
else
    echo "MongoDB already exists"
fi
echo ""

# Configure environment
echo "Configuring environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env file"
    echo "Edit it to add your API keys (TELEGRAM_BOT_TOKEN, NEWS_API_KEY)"
    read -p "Press Enter to edit now..."
    ${EDITOR:-vim} .env
fi
echo ""

# Initialize database
echo "Initializing database..."
pipenv run ntb db init
echo ""

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/news-tracker-bot.service > /dev/null <<EOF
[Unit]
Description=News Tracker Bot
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment="PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$HOME/.local/bin/pipenv run ntb bot start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
echo "Systemd service created"
echo ""

# Setup log rotation
echo "Setting up log rotation..."
sudo tee /etc/logrotate.d/news-tracker-bot > /dev/null <<EOF
$(pwd)/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $(whoami) $(whoami)
}
EOF
echo "Log rotation configured"
echo ""

# Setup automated cleanup
echo "Setting up automated cleanup..."
CRON_JOB="0 3 * * * cd $(pwd) && $HOME/.local/bin/pipenv run python -m news_tracker.scripts.cleanup >> $(pwd)/logs/cleanup.log 2>&1"
if ! crontab -l 2>/dev/null | grep -q "news_tracker.scripts.cleanup"; then
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Cleanup cron job added (runs daily at 3 AM)"
else
    echo "Cleanup cron job already exists"
fi
echo ""

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Log out and back in (for docker group)"
echo "2. Edit .env if needed: vim .env"
echo "3. Test: pipenv run ntb bot start"
echo "4. Run in background: sudo systemctl start news-tracker-bot"
echo "5. Enable on boot: sudo systemctl enable news-tracker-bot"
echo "6. Check status: sudo systemctl status news-tracker-bot"
echo "7. View logs: journalctl -u news-tracker-bot -f"
echo ""

