# Getting Started with News Tracker Bot

This tutorial will guide you through setting up and using the News Tracker Bot for the first time.

## What You'll Need

- A computer running Linux, macOS, or Windows (with WSL)
- Python 3.8 or higher installed
- Docker installed
- About 15 minutes

## Step 1: Get Your API Keys

### Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` to create a new bot
3. Choose a name (e.g., "My News Bot")
4. Choose a username ending in 'bot' (e.g., "mynews_bot")
5. Copy the token that looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### News API Key

1. Visit [NewsAPI.org](https://newsapi.org/)
2. Click "Get API Key" and sign up (free tier: 1000 requests/day)
3. Verify your email
4. Copy your API key from the dashboard

## Step 2: Install the Bot

```bash
# Clone the repository
git clone https://github.com/gajeshbhat/news-tracker-bot.git
cd news-tracker-bot

# Create environment file
cp .env.example .env
```

## Step 3: Configure

Edit the `.env` file with your favorite text editor:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_telegram_token_here
NEWS_API_KEY=your_newsapi_key_here

# Optional (defaults are fine)
TTS_ENGINE=edge
LOG_LEVEL=INFO
MONGO_URI=mongodb://localhost:27017/news_db
```

## Step 4: Start MongoDB

```bash
docker run -d \
    --name news-tracker-mongo \
    --restart unless-stopped \
    -p 27017:27017 \
    -v news-tracker-mongo-data:/data/db \
    mongo:7.0
```

Wait a few seconds for MongoDB to start, then verify:

```bash
docker ps | grep news-tracker-mongo
```

You should see the container running.

## Step 5: Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install project dependencies
pip install -e .
```

## Step 6: Initialize Database

```bash
ntb db init
```

You should see: "✅ Successfully loaded 127 news sources"

## Step 7: Generate Your Product Key

```bash
ntb keys generate --expires-in 365
```

**Important**: Save the key that's displayed! It looks like: `NTB-XXXX-XXXX-XXXX-XXXX`

## Step 8: Start the Bot

```bash
ntb bot start
```

You should see:
```
🤖 News Tracker Bot started successfully!
Press Ctrl+C to stop
```

## Step 9: Use Your Bot

1. **Open Telegram** and find your bot (search for the username you created)

2. **Send `/start`** to your bot

3. **Register** with your product key:
   ```
   /register NTB-XXXX-XXXX-XXXX-XXXX
   ```

4. **Get news** with `/latest`:
   - Select a news source (e.g., BBC News)
   - Choose format (Text, Audio, or Both)
   - Receive your personalized summary!

5. **Setup scheduled delivery** with `/schedule`:
   - Choose up to 2 news sources
   - Select format (text/audio/both)
   - Pick a time and timezone
   - Choose frequency (daily/weekdays/weekends)

## What's Next?

- **Explore more sources**: Try different news sources with `/latest`
- **Setup schedules**: Get automated news delivery with `/schedule`
- **Manage keys**: Learn CLI commands in the [CLI Reference](../reference/cli.md)
- **Customize**: Adjust settings in your `.env` file

## Troubleshooting

### Bot doesn't respond
- Check logs: `tail -f logs/news_tracker.log`
- Ensure MongoDB is running: `docker ps | grep mongo`

### MongoDB connection error
- Ensure MongoDB is running: `docker ps | grep news-tracker-mongo`
- Restart MongoDB: `docker restart news-tracker-mongo`

### "ntb: command not found"
- Activate venv: `source venv/bin/activate`
- Reinstall the package: `pip install -e .`

### Audio doesn't work
- Edge-TTS requires internet connection
- Check logs for TTS errors: `tail -f logs/errors.log`

## Stopping the Bot

Press `Ctrl+C` in the terminal where the bot is running.

To stop MongoDB:
```bash
docker stop news-tracker-mongo
```

## Next Steps

- Read the [Scheduling Guide](../how-to/scheduling.md) to learn about automated delivery
- Check the [CLI Reference](../reference/cli.md) for all available commands
- Explore different news sources and languages!

---

**Need help?** Open an issue on [GitHub](https://github.com/gajeshbhat/news-tracker-bot/issues)

