// MongoDB initialization script for News Tracker Bot
// This script creates the database and sets up initial collections with indexes

// Switch to the news_db database
db = db.getSiblingDB('news_db');

// Create a user for the news_db database
db.createUser({
  user: 'news_user',
  pwd: 'news_password',
  roles: [
    {
      role: 'readWrite',
      db: 'news_db'
    }
  ]
});

// Create collections with indexes for better performance
db.createCollection('news_sources');
db.createCollection('news_articles');

// Create indexes for efficient querying
db.news_sources.createIndex({ "search_id": 1 }, { unique: true });
db.news_sources.createIndex({ "name": 1 });
db.news_sources.createIndex({ "lang": 1 });

db.news_articles.createIndex({ "search_id": 1 });
db.news_articles.createIndex({ "name": 1 });
db.news_articles.createIndex({ "lang": 1 });

print('Database initialization completed successfully!');
