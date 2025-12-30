# 🤖 News Tracker Bot

> **Why read news when you can listen to it?**

A modern Telegram bot that delivers personalized news summaries in both text and audio formats. Get news from 127+ sources in 12+ languages, with high-quality AI voices.

## ✨ Features

- 📰 **Text & Audio Summaries** - Read or listen to news
- 🌍 **127+ News Sources** - BBC, CNN, Reuters, TechCrunch, and more
- 🎙️ **12+ Languages** - Multi-language support with Edge-TTS neural voices
- 📅 **Scheduled Delivery** - Automated news at your preferred time
- 🔐 **Product Key System** - Secure access control
- 💻 **CLI Administration** - Easy management via command line
- 🐳 **Docker Ready** - Simple deployment with MongoDB

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Docker
- Telegram Bot Token (from @BotFather)
- News API Key (from newsapi.org)

### Installation

```bash
# 1. Clone and setup
git clone https://github.com/gajeshbhat/news-tracker-bot.git
cd news-tracker-bot
cp .env.example .env

# 2. Edit .env with your tokens
# TELEGRAM_BOT_TOKEN=your_token_from_botfather
# NEWS_API_KEY=your_newsapi_key

# 3. Start MongoDB
docker run -d \
    --name news-tracker-mongo \
    --restart unless-stopped \
    -p 27017:27017 \
    -v news-tracker-mongo-data:/data/db \
    mongo:7.0

# 4. Create virtual environment and install
python3 -m venv venv
source venv/bin/activate
pip install -e .

# 5. Initialize database
ntb db init

# 6. Generate a product key
ntb keys generate --expires-in 365

# 7. Start the bot
ntb bot start
```

### First Use

1. Find your bot on Telegram
2. Send `/start`
3. Register with `/register NTB-XXXX-XXXX-XXXX-XXXX`
4. Try `/latest` to get news
5. Try `/schedule` to setup automated delivery

## 📱 Bot Commands

- `/start` - Welcome and registration
- `/help` - Show available commands
- `/latest` - Get news on demand
- `/schedule` - Setup automated delivery

## 💻 CLI Commands

```bash
# Product key management
ntb keys generate                    # Create new key
ntb keys list                        # View all keys
ntb keys revoke KEY                  # Revoke a key

# Bot management
ntb bot start                        # Start the bot
ntb bot status                       # Check status

# Database
ntb db init                          # Initialize database
ntb db stats                         # View statistics
```

## Documentation

- [Getting Started](docs/tutorials/getting-started.md) - Setup guide
- [Scheduling](docs/how-to/scheduling.md) - Automated delivery
- [Deployment](docs/how-to/deployment.md) - Production setup
- [Cleanup](docs/how-to/cleanup.md) - Storage management
- [CLI Reference](docs/reference/cli.md) - Commands

## 🔧 Technology Stack

- Python 3.12, python-telegram-bot
- MongoDB 7.0
- Edge-TTS (neural voices)
- Docker

## 📄 License

MIT License