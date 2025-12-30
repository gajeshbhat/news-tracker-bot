# News Tracker Bot - CLI Usage Guide

The News Tracker Bot includes a comprehensive command-line interface (CLI) for administration and management.

## Installation

After installing the package, you'll have access to two CLI commands:

```bash
news-tracker-bot --help
# or the shorter alias
ntb --help
```

## Command Structure

```
ntb [COMMAND] [SUBCOMMAND] [OPTIONS]
```

---

## Product Key Management

Product keys are used to control access to the bot. Users must register a valid product key before they can use the bot.

### Generate a New Key

```bash
# Generate a basic key
ntb keys generate

# Generate a key for a specific user
ntb keys generate --user-id 123456789 --username johndoe

# Generate a key that expires in 30 days
ntb keys generate --expires-in 30

# Generate a key with custom request limit
ntb keys generate --max-requests 500 --notes "Premium user"

# Full example
ntb keys generate \
  --user-id 123456789 \
  --username johndoe \
  --expires-in 90 \
  --max-requests 200 \
  --notes "Beta tester - expires Q2 2025"
```

**Output:**
```
✅ Product key generated successfully!

🔑 Key: NTB-A1B2-C3D4-E5F6-G7H8

⚠️  IMPORTANT: Save this key securely! It cannot be retrieved later.

Key Details:
  User ID: 123456789
  Username: johndoe
  Created: 2025-12-26 10:30:00 UTC
  Expires: 2025-03-26 10:30:00 UTC
  Max Requests/Day: 200
  Notes: Beta tester - expires Q2 2025
```

### List All Keys

```bash
# List active keys only
ntb keys list

# List all keys (including inactive and revoked)
ntb keys list --all
```

**Output includes Key ID** for easy management:
```
📋 Product Keys (2 total):

Key ID      | Key Hash        | User ID    | Username   | Created    | Status
694f1665... | c77193d74514... | 7561282893 | gajeshbhat | 2025-12-26 | ✅ Active
694f2266... | 1fcf9c8d3a71... | 9876543210 | johndoe    | 2025-12-27 | ❌ Inactive
```

💡 **Tip**: Copy the Key ID from this list to use in delete/revoke commands!

### Validate a Key

```bash
ntb keys validate NTB-A1B2-C3D4-E5F6-G7H8
```

### Assign Key to User

```bash
# Assign an unassigned key to a user
ntb keys assign NTB-A1B2-C3D4-E5F6-G7H8 --user-id 123456789 --username johndoe
```

### Revoke a Key

You can revoke a key in four ways:

```bash
# By product key (if you have it)
ntb keys revoke --key NTB-A1B2-C3D4-E5F6-G7H8

# By index number from list (easiest!)
ntb keys revoke --index 2

# By Telegram user ID (admin feature - no key needed!)
ntb keys revoke --user-id 123456789

# By Telegram username (admin feature - no key needed!)
ntb keys revoke --username johndoe
```

You'll be asked to confirm the revocation.

**💡 Admin Tip**: Use `--index` for quick revocation, or `--user-id`/`--username` to revoke without needing the actual product key!

### Cleanup Expired Keys

```bash
# Automatically deactivate all expired keys
ntb keys cleanup
```

### Get User Key Information

```bash
# Get key details by user ID (shows ALL keys for this user)
ntb keys info --user-id 123456789

# Get key details by username (shows ALL keys for this user)
ntb keys info --username johndoe
```

**Output:**
```
📋 Product Keys for this user (2 total):

Key #1:
  Key ID: 694f1665490d35c484d00d8b
  User ID: 123456789
  Username: johndoe
  Created: 2025-12-26 10:30:00 UTC
  Expires: 2026-12-26 10:30:00 UTC
  Max Requests/Day: 100
  Status: ✅ Active
  Notes: Annual subscription

Key #2:
  Key ID: 694f2266490d35c484d00d9c
  User ID: 123456789
  Username: johndoe
  Created: 2025-11-15 08:20:00 UTC
  Expires: Never
  Max Requests/Day: 50
  Status: ❌ Inactive
  Notes: Old trial key
```

💡 **Note**: Users can have multiple keys (e.g., trial + paid, or renewed subscriptions)

### Delete Product Keys

**⚠️ WARNING**: Delete permanently removes keys from the database. Use `revoke` to just deactivate.

```bash
# Delete by index number from list (easiest!)
ntb keys delete --index 2

# Delete a specific key by ID (safest - deletes only one key)
ntb keys delete --key-id 694f1665490d35c484d00d8b

# Delete ALL keys for a user ID (use with caution!)
ntb keys delete --user-id 123456789

# Delete ALL keys for a username (use with caution!)
ntb keys delete --username johndoe
```

**Confirmation required:**
```
⚠️  WARNING: You are about to PERMANENTLY DELETE 2 key(s) for user ID: 123456789
⚠️  This action CANNOT be undone!
Are you absolutely sure? [y/N]:
```

**When to use DELETE vs REVOKE:**
- **REVOKE** (`ntb keys revoke`): Temporarily disable access (can be reactivated)
- **DELETE** (`ntb keys delete`): Permanently remove from database (cannot be undone)

💡 **Best Practice**: Use REVOKE for temporary bans, DELETE only for cleanup or GDPR requests

---

## Bot Management

### Start the Bot

```bash
# Start in foreground (for testing)
ntb bot start

# Start as daemon (background) - requires systemd setup
ntb bot start --daemon
```

### Check Bot Status

```bash
ntb bot status
```

---

## Database Management

### Initialize Database

```bash
# Populate database with news sources
ntb db init
```

This fetches all available news sources from NewsAPI and stores them in MongoDB.

### Database Statistics

```bash
# View database stats
ntb db stats
```

**Output:**
```
📊 Database Statistics:

  News Sources: 127
  Articles: 1,543
  Product Keys: 15 (12 active)
```

---

## Configuration

### View Current Configuration

```bash
ntb config --show
```

**Output:**
```
⚙️  Current Configuration:

  MongoDB URI: mongodb://localhost:27017/news_db
  TTS Engine: edge
  Audio Directory: data/audio
  Log Level: INFO
  Log Directory: logs
```

---

## Common Workflows

### Onboarding a New User

1. Generate a product key:
   ```bash
   ntb keys generate --expires-in 365 --notes "Annual subscription"
   ```

2. Send the key to the user

3. User registers in Telegram:
   ```
   /register NTB-XXXX-XXXX-XXXX-XXXX
   ```

4. Verify registration:
   ```bash
   ntb keys list
   ```

### Monthly Maintenance

```bash
# Cleanup expired keys
ntb keys cleanup

# View database stats
ntb db stats

# Check bot status
ntb bot status
```

### Revoking User Access (Admin)

**Scenario**: User violated terms, need to revoke access immediately

```bash
# Step 1: Find the user's keys
ntb keys list --all | grep johndoe
# Or
ntb keys info --username johndoe

# Step 2: Revoke access (deactivates but keeps in database)
ntb keys revoke --username johndoe

# Alternative: Revoke by user ID
ntb keys revoke --user-id 123456789

# Alternative: Revoke specific key by ID
ntb keys revoke --key-id 694f1665490d35c484d00d8b
```

### Deleting User Data (Admin)

**Scenario**: User requested account deletion (GDPR compliance)

```bash
# Step 1: Check what will be deleted
ntb keys info --user-id 123456789

# Step 2: Permanently delete ALL keys for this user
ntb keys delete --user-id 123456789

# Alternative: Delete specific key only
ntb keys delete --key-id 694f1665490d35c484d00d8b
```

### Managing Users with Multiple Keys

**Scenario**: User has multiple keys (trial expired, now has paid subscription)

```bash
# Step 1: View all keys for user
ntb keys info --user-id 123456789

# Output shows:
# Key #1: 694f1665... (Inactive - old trial)
# Key #2: 694f2266... (Active - current subscription)

# Step 2: Delete only the old trial key
ntb keys delete --key-id 694f1665490d35c484d00d8b

# Or revoke all and keep only active
ntb keys list --all | grep 123456789  # Review
ntb keys delete --key-id <old_key_id>  # Delete each old key
```

### Troubleshooting

```bash
# Check configuration
ntb config --show

# Verify database connection
ntb db stats

# Check if keys are working
ntb keys list

# Validate a specific key
ntb keys validate NTB-XXXX-XXXX-XXXX-XXXX

# Get info about a specific user
ntb keys info --user-id 123456789
```

---

## Environment Variables

The CLI respects the same environment variables as the bot:

- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `NEWS_API_KEY` - NewsAPI key
- `MONGO_URI` - MongoDB connection string
- `TTS_ENGINE` - Text-to-speech engine (edge/gtts/pyttsx3)
- `LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)

Make sure your `.env` file is properly configured before using the CLI.

---

## Tips

1. **Use the short alias**: `ntb` is faster to type than `news-tracker-bot`

2. **Tab completion**: Most shells support tab completion for commands

3. **Help is always available**: Add `--help` to any command
   ```bash
   ntb --help
   ntb keys --help
   ntb keys generate --help
   ```

4. **Pipe output**: CLI output can be piped to other commands
   ```bash
   ntb keys list | grep "Active"
   ```

5. **Automation**: Use CLI commands in scripts
   ```bash
   #!/bin/bash
   # Daily cleanup script
   ntb keys cleanup
   ntb db stats
   ```

---

## Security Best Practices

1. **Protect product keys**: Never commit keys to version control
2. **Use expiration**: Set expiration dates for temporary access
3. **Regular cleanup**: Run `ntb keys cleanup` regularly
4. **Monitor usage**: Check `ntb db stats` to monitor activity
5. **Revoke compromised keys**: Immediately revoke any compromised keys

---

## Next Steps

- [Security Setup Guide](SECURITY_SETUP.md)
- [Administration Guide](ADMINISTRATION.md)
- [Deployment Guide](../README.md)

