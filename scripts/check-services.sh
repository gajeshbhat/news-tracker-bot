#!/bin/bash

# Service Health Check Script
set -e

echo "🔍 Checking News Tracker Bot Services..."
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
else
    echo "✅ Docker is installed"
fi

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available"
    exit 1
else
    echo "✅ Docker Compose is available"
fi

# Check if MongoDB container is running
if docker compose ps mongodb | grep -q "Up"; then
    echo "✅ MongoDB container is running"

    # Check MongoDB connection
    if docker compose exec -T mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        echo "✅ MongoDB is responding to connections"
    else
        echo "❌ MongoDB is not responding"
        exit 1
    fi
else
    echo "❌ MongoDB container is not running"
    echo "   Run: docker compose up -d mongodb"
    exit 1
fi

# Check Python environment
if command -v pipenv &> /dev/null; then
    echo "✅ Pipenv is installed"
    
    # Check if virtual environment exists
    if pipenv --venv &> /dev/null; then
        echo "✅ Python virtual environment exists"
        
        # Test imports
        if pipenv run python -c "import api.news_modules, bot.bot_modules, start_bot" &> /dev/null; then
            echo "✅ All Python modules can be imported"
        else
            echo "❌ Python module import failed"
            echo "   Run: pipenv install"
            exit 1
        fi
    else
        echo "❌ Python virtual environment not found"
        echo "   Run: pipenv install"
        exit 1
    fi
else
    echo "❌ Pipenv is not installed"
    exit 1
fi

# Check .env file
if [ -f .env ]; then
    echo "✅ .env file exists"
    
    # Check if API keys are set
    if grep -q "your_telegram_bot_token_here" .env || grep -q "your_news_api_key_here" .env; then
        echo "⚠️  API keys not configured in .env file"
    else
        echo "✅ API keys appear to be configured"
    fi
else
    echo "❌ .env file not found"
    echo "   Run: cp .env.example .env"
    exit 1
fi

echo ""
echo "🎉 All services are healthy and ready!"
echo ""
echo "To start the bot:"
echo "  make start"
echo "  # or"
echo "  pipenv run python start_bot.py"
