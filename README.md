# 🤖 Hello World News Tracker Bot

> **Why read news when you can listen to it?**

A modern Telegram bot that delivers personalized news summaries in both text and audio formats. Originally built in 2016, completely modernized in 2025 with Docker integration and AI-powered text-to-speech.

## ✨ Features

- 📰 **Text Summaries** - Breaking news with clickable links
- 🔊 **Audio Summaries** - High-quality AI voices in 75+ languages
- 🌍 **127+ News Sources** - BBC, CNN, Reuters, TechCrunch, and more
- 🎙️ **Multiple TTS Engines** - Edge-TTS (neural), Google TTS, offline options
- ⚡ **Real-time Updates** - Fresh news on demand
- 🐳 **Docker Ready** - Easy deployment with persistent storage

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** (3.12+ recommended)
- **Docker & Docker Compose** (for MongoDB)
- **Telegram Bot Token**
- **News API Key**

### 📱 Step 1: Create Your Telegram Bot

1. **Open Telegram** and search for [@BotFather](https://t.me/BotFather)
2. **Start a chat** and send `/newbot`
3. **Choose a name** for your bot (e.g., "My News Tracker")
4. **Choose a username** (must end in 'bot', e.g., "mynews_tracker_bot")
5. **Copy the token** - you'll need this for the `.env` file

```
🤖 BotFather will give you a token like:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 🗞️ Step 2: Get Your News API Key

1. **Visit** [NewsAPI.org](https://newsapi.org/)
2. **Click "Get API Key"** and sign up (free tier: 1000 requests/day)
3. **Verify your email** and log in
4. **Copy your API key** from the dashboard

```
🔑 Your API key will look like:
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### ⚙️ Step 3: Setup the Bot

1. **Clone the repository**
   ```bash
   git clone https://github.com/gajeshbhat/Hello-World-News.git
   cd Hello-World-News
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` with your keys**
   ```bash
   # Required - Add your actual tokens
   SHABDA_TELE_KEY=YOUR_TELEGRAM_BOT_TOKEN
   NEWS_API_KEY=YOUR_NEWS_API_KEY

   # Optional - Customize settings
   TTS_ENGINE=edge # Best quality AI voices
   LOG_LEVEL=INFO
   MONGO_URI=mongodb://localhost:27017/news_db
   ```

4. **Start MongoDB**
   ```bash
   docker compose up -d mongodb
   ```

5. **Install dependencies**
   ```bash
   pip install pipenv
   pipenv install
   ```

6. **Initialize database**
   ```bash
   pipenv run python setup_database.py
   ```

7. **Start the bot**
   ```bash
   pipenv run python run_bot.py
   ```

### 🎉 Step 4: Test Your Bot

1. **Find your bot** on Telegram (search for the username you created)
2. **Send `/start`** to begin
3. **Try `/latest`** to see available news sources
4. **Select a source** and choose your preferred format!

## 🎙️ Text-to-Speech Options

The bot supports multiple TTS engines with automatic fallback:

### 🌟 **Edge-TTS** (Recommended)
- **Quality**: ⭐⭐⭐⭐⭐ (Neural AI voices)
- **Languages**: 100+ with natural pronunciation
- **Cost**: Free (Microsoft's service)
- **Setup**: Works out of the box

### 🌐 **Google TTS**
- **Quality**: ⭐⭐⭐⭐ (Good quality)
- **Languages**: 75+ languages
- **Cost**: Free (with usage limits)
- **Setup**: Works out of the box

### 💻 **pyttsx3** (Offline)
- **Quality**: ⭐⭐⭐ (Basic but reliable)
- **Languages**: System dependent
- **Cost**: Free (completely offline)
- **Setup**: Uses your system's TTS engine

### 🔧 TTS Configuration

In your `.env` file:
```bash
# Choose your preferred engine
TTS_ENGINE=edge     # Best quality (default)
TTS_ENGINE=gtts     # Good quality, reliable
TTS_ENGINE=pyttsx3  # Offline, basic quality

# Customize audio storage
AUDIO_DIR=data/audio
```

## 🐳 Docker & Database

### MongoDB Setup
The bot uses MongoDB for storing news sources and articles:

```bash
# Start MongoDB (persistent storage)
docker compose up -d mongodb

# View MongoDB logs
docker compose logs -f mongodb

# Stop MongoDB
docker compose down

# Clean up (⚠️ deletes all data)
docker compose down -v
```

### Database Management
```bash
# Initialize with news sources
pipenv run python setup_database.py

# Access MongoDB shell
docker compose exec mongodb mongosh news_db

# Check collections
show collections
db.news_sources.countDocuments()
```

## 📱 Bot Usage

Once your bot is running, users can interact with it:

### Commands
- `/start` - Welcome message and introduction
- `/help` - Show available commands and features
- `/latest` - Browse news sources and get summaries

### User Flow
1. **User sends** `/latest`
2. **Bot shows** available news sources (BBC, CNN, etc.)
3. **User selects** a news source
4. **Bot offers** format options: Text, Audio, or Both
5. **Bot delivers** personalized summary

### Example Interaction
```
User: /latest
Bot: 📰 Choose a news source: [BBC News] [CNN] [Reuters]...

User: BBC News
Bot: 📰 Selected: BBC News
     Choose format: [Text Summary] [Audio Summary] [Both]

User: Both
Bot: 📰 Fetching latest news...
     [Text summary with links]
     🔊 [Audio file]
```

## Configuration

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `SHABDA_TELE_KEY` | Telegram Bot Token | Required |
| `NEWS_API_KEY` | News API Key | Required |
| `MONGO_URI` | MongoDB Connection | `mongodb://localhost:27017/news_db` |
| `TTS_ENGINE` | TTS Engine | `edge` |
| `LOG_LEVEL` | Logging Level | `INFO` |
| `AUDIO_DIR` | Audio Storage | `data/audio` |

## 📊 Logging

Professional logging system with rotating files:

- **Main logs**: `logs/news_tracker.log`
- **Errors only**: `logs/errors.log`
- **API calls**: `logs/api_calls.log`
- **Bot interactions**: `logs/bot_interactions.log`

```bash
# View logs in real-time
tail -f logs/news_tracker.log

# Check error logs
tail -f logs/errors.log
```

## 🚀 Advanced Usage

### Custom Commands
```bash
# Start with custom log level
LOG_LEVEL=DEBUG pipenv run python run_bot.py

# Use different TTS engine
TTS_ENGINE=gtts pipenv run python run_bot.py

# Custom MongoDB URI
MONGO_URI=mongodb://user:pass@host:port/db pipenv run python run_bot.py
```

### Development Mode
```bash
# Install development dependencies
pipenv install --dev

# Run with debug logging
LOG_LEVEL=DEBUG pipenv run python run_bot.py

# Test imports
pipenv run python -c "import news_tracker; print('✅ Package OK')"
```

## 📄 License & Credits

- **Originally built in 2017** as a second-year CS student project
- **Open source** - feel free to contribute!

## 🌟 Star History

If this project helped you, please consider giving it a ⭐!

---

**Built with ❤️ by [Gajesh](https://www.gajeshbhat.com)**