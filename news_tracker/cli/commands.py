"""
CLI Commands for News Tracker Bot Administration
Provides command-line interface for managing the bot
"""

import click
import sys
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

from ..core.product_keys import ProductKeyManager
from ..core.config import get_config
from ..utils.logging_config import get_logger


@click.group()
@click.version_option(version='2.0.0', prog_name='news-tracker-bot')
def cli():
    """News Tracker Bot - Administration CLI"""
    pass


@cli.group()
def keys():
    """Manage product keys for user authentication"""
    pass


@keys.command('generate')
@click.option('--user-id', type=int, help='Telegram user ID')
@click.option('--username', type=str, help='Telegram username')
@click.option('--expires-in', type=int, help='Days until expiration (default: never)')
@click.option('--max-requests', type=int, default=100, help='Max requests per day (default: 100)')
@click.option('--notes', type=str, default='', help='Additional notes')
def generate_key(user_id, username, expires_in, max_requests, notes):
    """Generate a new product key"""
    try:
        manager = ProductKeyManager()
        
        plain_key, product_key = manager.generate_key(
            user_id=user_id,
            username=username,
            expires_in_days=expires_in,
            max_requests_per_day=max_requests,
            notes=notes
        )
        
        click.echo("\n✅ Product key generated successfully!\n")
        click.echo(f"🔑 Key: {click.style(plain_key, fg='green', bold=True)}")
        click.echo(f"\n⚠️  IMPORTANT: Save this key securely! It cannot be retrieved later.\n")
        
        # Show key details
        click.echo("Key Details:")
        click.echo(f"  User ID: {product_key.user_id or 'Not assigned'}")
        click.echo(f"  Username: {product_key.username or 'Not assigned'}")
        click.echo(f"  Created: {product_key.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        click.echo(f"  Expires: {product_key.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC') if product_key.expires_at else 'Never'}")
        click.echo(f"  Max Requests/Day: {product_key.max_requests_per_day}")
        if notes:
            click.echo(f"  Notes: {notes}")
        
    except Exception as e:
        click.echo(f"❌ Error generating key: {e}", err=True)
        sys.exit(1)


@keys.command('list')
@click.option('--all', 'show_all', is_flag=True, help='Show inactive keys too')
def list_keys(show_all):
    """List all product keys"""
    try:
        manager = ProductKeyManager()
        keys_list = manager.list_keys(active_only=not show_all)

        if not keys_list:
            click.echo("No product keys found.")
            return

        # Prepare table data
        table_data = []
        for idx, key in enumerate(keys_list, 1):
            status = "✅ Active" if key.is_active else "❌ Inactive"

            # Check if expired
            if key.expires_at and key.expires_at < datetime.utcnow():
                status = "⏰ Expired"

            table_data.append([
                idx,  # Add index number
                key.key_id if key.key_id else "N/A",  # Show full Key ID
                key.key_hash[:12] + "...",
                key.user_id or "N/A",
                key.username or "N/A",
                key.created_at.strftime('%Y-%m-%d'),
                key.expires_at.strftime('%Y-%m-%d') if key.expires_at else "Never",
                key.max_requests_per_day,
                status,
                key.notes[:20] + "..." if len(key.notes) > 20 else key.notes
            ])

        headers = ["#", "Key ID", "Key Hash", "User ID", "Username", "Created", "Expires", "Max Req/Day", "Status", "Notes"]
        click.echo(f"\n📋 Product Keys ({len(keys_list)} total):\n")
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
        click.echo("\n💡 Tip: Use the Key ID to delete/revoke keys, or use --index with the # number")

    except Exception as e:
        click.echo(f"❌ Error listing keys: {e}", err=True)
        sys.exit(1)


@keys.command('validate')
@click.argument('key')
def validate_key(key):
    """Validate a product key"""
    try:
        manager = ProductKeyManager()
        product_key = manager.validate_key(key)
        
        if product_key:
            click.echo(f"\n✅ Key is valid!\n")
            click.echo("Key Details:")
            click.echo(f"  User ID: {product_key.user_id or 'Not assigned'}")
            click.echo(f"  Username: {product_key.username or 'Not assigned'}")
            click.echo(f"  Created: {product_key.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            click.echo(f"  Expires: {product_key.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC') if product_key.expires_at else 'Never'}")
            click.echo(f"  Max Requests/Day: {product_key.max_requests_per_day}")
            if product_key.notes:
                click.echo(f"  Notes: {product_key.notes}")
        else:
            click.echo("❌ Invalid, inactive, or expired key", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error validating key: {e}", err=True)
        sys.exit(1)


@keys.command('revoke')
@click.option('--key', type=str, help='Product key to revoke')
@click.option('--index', type=int, help='Revoke by index number (# from list command)')
@click.option('--user-id', type=int, help='Revoke by Telegram user ID')
@click.option('--username', type=str, help='Revoke by Telegram username')
def revoke_key(key, index, user_id, username):
    """Revoke a product key (by key, index, user ID, or username)"""
    try:
        manager = ProductKeyManager()

        # Validate that at least one option is provided
        if not any([key, index, user_id, username]):
            click.echo("❌ Error: Must provide --key, --index, --user-id, or --username", err=True)
            click.echo("\nExamples:")
            click.echo("  ntb keys revoke --key NTB-XXXX-XXXX-XXXX-XXXX")
            click.echo("  ntb keys revoke --index 2")
            click.echo("  ntb keys revoke --user-id 123456789")
            click.echo("  ntb keys revoke --username johndoe")
            sys.exit(1)

        # Handle index-based revocation
        if index:
            # Get all keys to find the one at the index
            keys_list = manager.list_keys(active_only=False)
            if index < 1 or index > len(keys_list):
                click.echo(f"❌ Invalid index: {index}. Valid range is 1-{len(keys_list)}", err=True)
                sys.exit(1)

            # Get the key at the index (index is 1-based)
            target_key = keys_list[index - 1]
            key_id = target_key.key_id

            # Show what will be revoked
            click.echo(f"\n📋 Key #{index} details:")
            click.echo(f"  Key ID: {key_id}")
            click.echo(f"  User ID: {target_key.user_id or 'N/A'}")
            click.echo(f"  Username: {target_key.username or 'N/A'}")
            click.echo(f"  Notes: {target_key.notes}")
            click.echo()

            # Revoke by key_id
            target = f"key #{index}"
        elif key:
            target = f"key: {key}"
        elif user_id:
            target = f"user ID: {user_id}"
        else:
            target = f"username: {username}"

        # Confirm revocation
        click.echo(f"⚠️  You are about to revoke {target}")
        if not click.confirm("Are you sure?"):
            click.echo("Cancelled")
            return

        # Perform revocation
        success = False
        if index:
            # Revoke by key_id (already set above)
            success = manager.revoke_key_by_key_id(key_id)
        elif key:
            success = manager.revoke_key(key)
        elif user_id:
            success = manager.revoke_key_by_user_id(user_id)
        else:
            success = manager.revoke_key_by_username(username)

        if success:
            click.echo(f"✅ Key revoked successfully")
        else:
            click.echo(f"❌ Failed to revoke - not found", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error revoking key: {e}", err=True)
        sys.exit(1)


@keys.command('assign')
@click.argument('key')
@click.option('--user-id', type=int, required=True, help='Telegram user ID')
@click.option('--username', type=str, help='Telegram username')
def assign_key(key, user_id, username):
    """Assign a product key to a user"""
    try:
        manager = ProductKeyManager()
        
        if manager.assign_key_to_user(key, user_id, username):
            click.echo(f"✅ Key assigned to user {user_id}")
        else:
            click.echo("❌ Failed to assign key", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error assigning key: {e}", err=True)
        sys.exit(1)


@keys.command('cleanup')
def cleanup_keys():
    """Cleanup expired product keys"""
    try:
        manager = ProductKeyManager()
        count = manager.cleanup_expired_keys()

        if count > 0:
            click.echo(f"✅ Deactivated {count} expired key(s)")
        else:
            click.echo("ℹ️  No expired keys found")

    except Exception as e:
        click.echo(f"❌ Error cleaning up keys: {e}", err=True)
        sys.exit(1)


@keys.command('info')
@click.option('--user-id', type=int, help='Get key info by Telegram user ID')
@click.option('--username', type=str, help='Get key info by Telegram username')
def key_info(user_id, username):
    """Get detailed information about a user's product key(s)"""
    try:
        manager = ProductKeyManager()

        # Validate that at least one option is provided
        if not any([user_id, username]):
            click.echo("❌ Error: Must provide --user-id or --username", err=True)
            click.echo("\nExamples:")
            click.echo("  ntb keys info --user-id 123456789")
            click.echo("  ntb keys info --username johndoe")
            sys.exit(1)

        # Get all keys for the user
        keys = []
        if user_id:
            keys = manager.get_all_keys_by_user_id(user_id)
        else:
            keys = manager.get_all_keys_by_username(username)

        if not keys:
            click.echo(f"❌ No keys found for this user", err=True)
            sys.exit(1)

        # Display key information
        click.echo(f"\n📋 Product Keys for this user ({len(keys)} total):\n")

        for idx, key in enumerate(keys, 1):
            if len(keys) > 1:
                click.echo(f"Key #{idx}:")

            click.echo(f"  Key ID: {key.key_id}")
            click.echo(f"  User ID: {key.user_id or 'Not assigned'}")
            click.echo(f"  Username: {key.username or 'Not assigned'}")
            click.echo(f"  Created: {key.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")

            if key.expires_at:
                click.echo(f"  Expires: {key.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            else:
                click.echo(f"  Expires: Never")

            click.echo(f"  Max Requests/Day: {key.max_requests_per_day}")
            click.echo(f"  Status: {'✅ Active' if key.is_active else '❌ Inactive'}")

            if key.notes:
                click.echo(f"  Notes: {key.notes}")

            if idx < len(keys):
                click.echo()

        click.echo()

    except Exception as e:
        click.echo(f"❌ Error getting key info: {e}", err=True)
        sys.exit(1)


@keys.command('delete')
@click.option('--key-id', type=str, help='Delete by key ID (from list command)')
@click.option('--index', type=int, help='Delete by index number (# from list command)')
@click.option('--user-id', type=int, help='Delete ALL keys for this Telegram user ID')
@click.option('--username', type=str, help='Delete ALL keys for this Telegram username')
def delete_key(key_id, index, user_id, username):
    """Permanently delete product key(s) from database"""
    try:
        manager = ProductKeyManager()

        # Validate that at least one option is provided
        if not any([key_id, index, user_id, username]):
            click.echo("❌ Error: Must provide --key-id, --index, --user-id, or --username", err=True)
            click.echo("\nExamples:")
            click.echo("  ntb keys delete --key-id 67890abc12345def")
            click.echo("  ntb keys delete --index 2")
            click.echo("  ntb keys delete --user-id 123456789")
            click.echo("  ntb keys delete --username johndoe")
            sys.exit(1)

        # Handle index-based deletion
        if index:
            # Get all keys to find the one at the index
            keys_list = manager.list_keys(active_only=False)
            if index < 1 or index > len(keys_list):
                click.echo(f"❌ Invalid index: {index}. Valid range is 1-{len(keys_list)}", err=True)
                sys.exit(1)

            # Get the key at the index (index is 1-based)
            target_key = keys_list[index - 1]
            key_id = target_key.key_id

            # Show what will be deleted
            click.echo(f"\n📋 Key #{index} details:")
            click.echo(f"  Key ID: {key_id}")
            click.echo(f"  User ID: {target_key.user_id or 'N/A'}")
            click.echo(f"  Username: {target_key.username or 'N/A'}")
            click.echo(f"  Notes: {target_key.notes}")
            click.echo()

        # Show what will be deleted
        if key_id:
            target = f"key ID: {key_id}"
            count_msg = "1 key"
        elif user_id:
            keys = manager.get_all_keys_by_user_id(user_id)
            target = f"user ID: {user_id}"
            count_msg = f"{len(keys)} key(s)"
        else:
            keys = manager.get_all_keys_by_username(username)
            target = f"username: {username}"
            count_msg = f"{len(keys)} key(s)"

        # Confirm deletion
        click.echo(f"⚠️  WARNING: You are about to PERMANENTLY DELETE {count_msg} for {target}")
        click.echo("⚠️  This action CANNOT be undone!")
        if not click.confirm("Are you absolutely sure?"):
            click.echo("Cancelled")
            return

        # Perform deletion
        if key_id:
            success = manager.delete_key_by_id(key_id)
            if success:
                click.echo(f"✅ Key deleted successfully")
            else:
                click.echo(f"❌ Failed to delete - key not found", err=True)
                sys.exit(1)
        elif user_id:
            count = manager.delete_keys_by_user_id(user_id)
            if count > 0:
                click.echo(f"✅ Deleted {count} key(s) successfully")
            else:
                click.echo(f"❌ No keys found for this user", err=True)
                sys.exit(1)
        else:
            count = manager.delete_keys_by_username(username)
            if count > 0:
                click.echo(f"✅ Deleted {count} key(s) successfully")
            else:
                click.echo(f"❌ No keys found for this user", err=True)
                sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error deleting key: {e}", err=True)
        sys.exit(1)


@cli.group()
def bot():
    """Manage the bot server"""
    pass


@bot.command('start')
@click.option('--daemon', '-d', is_flag=True, help='Run as daemon in background')
def start_bot(daemon):
    """Start the bot server"""
    if daemon:
        click.echo("🚀 Starting bot in daemon mode...")
        # TODO: Implement daemon mode with systemd or supervisor
        click.echo("⚠️  Daemon mode not yet implemented. Use systemd service instead.")
    else:
        click.echo("🚀 Starting bot in foreground mode...")
        from ..main import run
        sys.exit(run())


@bot.command('status')
def bot_status():
    """Check bot server status"""
    # TODO: Implement status check (check if process is running, check MongoDB connection, etc.)
    click.echo("ℹ️  Status check not yet implemented")


@cli.group()
def db():
    """Database management commands"""
    pass


@db.command('init')
def init_database():
    """Initialize database with news sources"""
    try:
        click.echo("🔄 Initializing database...")
        from ..scripts.setup_database import main as setup_db
        result = setup_db()
        
        if result == 0:
            click.echo("✅ Database initialized successfully")
        else:
            click.echo("❌ Database initialization failed", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error initializing database: {e}", err=True)
        sys.exit(1)


@db.command('stats')
def database_stats():
    """Show database statistics"""
    try:
        from pymongo import MongoClient
        from ..core.config import get_mongo_uri
        
        client = MongoClient(get_mongo_uri())
        db = client.get_database()
        
        click.echo("\n📊 Database Statistics:\n")
        
        # News sources
        sources_count = db.news_sources.count_documents({})
        click.echo(f"  News Sources: {sources_count}")
        
        # Articles
        articles_count = db.articles.count_documents({})
        click.echo(f"  Articles: {articles_count}")
        
        # Product keys
        keys_count = db.product_keys.count_documents({})
        active_keys = db.product_keys.count_documents({'is_active': True})
        click.echo(f"  Product Keys: {keys_count} ({active_keys} active)")
        
        click.echo()
        
    except Exception as e:
        click.echo(f"❌ Error getting database stats: {e}", err=True)
        sys.exit(1)


@cli.command('config')
@click.option('--show', is_flag=True, help='Show current configuration')
def config_command(show):
    """Manage configuration"""
    if show:
        try:
            config = get_config()
            click.echo("\n⚙️  Current Configuration:\n")
            click.echo(f"  MongoDB URI: {config.database.mongo_uri}")
            click.echo(f"  TTS Engine: {config.tts.preferred_engine}")
            click.echo(f"  Audio Directory: {config.tts.audio_output_dir}")
            click.echo(f"  Log Level: {config.logging.level}")
            click.echo(f"  Log Directory: {config.logging.log_dir}")
            click.echo()
        except Exception as e:
            click.echo(f"❌ Error loading configuration: {e}", err=True)
            sys.exit(1)
    else:
        click.echo("Use --show to display current configuration")


if __name__ == '__main__':
    cli()

