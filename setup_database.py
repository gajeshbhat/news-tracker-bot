#!/usr/bin/env python3
"""
Database setup script for News Tracker Bot
Run this to initialize the database
"""

import sys
from news_tracker.scripts.setup_database import main

if __name__ == "__main__":
    sys.exit(main())
