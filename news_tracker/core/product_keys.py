"""
Product Key Management System
Secure key generation and validation for user access control
"""

import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
import pymongo
from pymongo import MongoClient

from .config import get_mongo_uri
from ..utils.logging_config import get_logger


@dataclass
class ProductKey:
    """Product key data structure"""
    key_hash: str
    user_id: Optional[int] = None  # Telegram user ID
    username: Optional[str] = None  # Telegram username
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    max_requests_per_day: int = 100
    notes: str = ""
    key_id: Optional[str] = None  # MongoDB _id as string

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage"""
        data = asdict(self)
        # Remove key_id as it's stored as _id in MongoDB
        data.pop('key_id', None)
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProductKey':
        """Create from MongoDB document"""
        # Convert MongoDB _id to key_id string
        clean_data = {k: v for k, v in data.items() if k != '_id'}
        if '_id' in data:
            clean_data['key_id'] = str(data['_id'])
        return cls(**clean_data)


class ProductKeyManager:
    """Manages product keys for user authentication"""
    
    # Key format: NTB-XXXX-XXXX-XXXX-XXXX (News Tracker Bot)
    KEY_PREFIX = "NTB"
    KEY_LENGTH = 32  # bytes of entropy
    HASH_ALGORITHM = "sha256"
    
    def __init__(self, mongo_uri: Optional[str] = None):
        """Initialize product key manager"""
        self.logger = get_logger('product_keys')
        self.mongo_uri = mongo_uri or get_mongo_uri()
        
        # Connect to MongoDB
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client.get_database()
        self.keys_collection = self.db['product_keys']
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for efficient queries"""
        try:
            # Index on key_hash for fast lookups
            self.keys_collection.create_index('key_hash', unique=True)
            
            # Index on user_id for user-based queries
            self.keys_collection.create_index('user_id')
            
            # Index on is_active for filtering
            self.keys_collection.create_index('is_active')
            
            # Index on expires_at for cleanup
            self.keys_collection.create_index('expires_at')
            
            self.logger.info("Product key indexes created successfully")
        except Exception as e:
            self.logger.error(f"Error creating indexes: {e}")
    
    def _generate_random_key(self) -> str:
        """Generate a cryptographically secure random key"""
        # Generate random bytes
        random_bytes = secrets.token_bytes(self.KEY_LENGTH)
        
        # Convert to hex string
        hex_key = random_bytes.hex().upper()
        
        # Format as NTB-XXXX-XXXX-XXXX-XXXX
        parts = [hex_key[i:i+4] for i in range(0, len(hex_key), 4)]
        formatted_key = f"{self.KEY_PREFIX}-{'-'.join(parts[:4])}"
        
        return formatted_key
    
    def _hash_key(self, key: str) -> str:
        """Hash a product key for secure storage"""
        # Use SHA-256 for hashing
        key_bytes = key.encode('utf-8')
        hash_obj = hashlib.sha256(key_bytes)
        return hash_obj.hexdigest()
    
    def generate_key(
        self,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        max_requests_per_day: int = 100,
        notes: str = ""
    ) -> tuple[str, ProductKey]:
        """
        Generate a new product key
        
        Args:
            user_id: Telegram user ID (optional, can be assigned later)
            username: Telegram username (optional)
            expires_in_days: Number of days until expiration (None = never expires)
            max_requests_per_day: Maximum API requests per day
            notes: Additional notes about this key
        
        Returns:
            Tuple of (plain_key, ProductKey object)
        """
        try:
            # Generate random key
            plain_key = self._generate_random_key()
            
            # Hash the key for storage
            key_hash = self._hash_key(plain_key)
            
            # Calculate expiration
            expires_at = None
            if expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            
            # Create ProductKey object
            product_key = ProductKey(
                key_hash=key_hash,
                user_id=user_id,
                username=username,
                expires_at=expires_at,
                max_requests_per_day=max_requests_per_day,
                notes=notes
            )
            
            # Store in database
            self.keys_collection.insert_one(product_key.to_dict())
            
            self.logger.info(f"Generated new product key for user_id={user_id}, username={username}")
            
            return plain_key, product_key
            
        except pymongo.errors.DuplicateKeyError:
            # Extremely rare collision, try again
            self.logger.warning("Key collision detected, regenerating...")
            return self.generate_key(user_id, username, expires_in_days, max_requests_per_day, notes)
        except Exception as e:
            self.logger.error(f"Error generating product key: {e}")
            raise
    
    def validate_key(self, plain_key: str) -> Optional[ProductKey]:
        """
        Validate a product key
        
        Args:
            plain_key: The plain text product key
        
        Returns:
            ProductKey object if valid, None otherwise
        """
        try:
            # Hash the provided key
            key_hash = self._hash_key(plain_key)
            
            # Look up in database
            key_doc = self.keys_collection.find_one({'key_hash': key_hash})
            
            if not key_doc:
                self.logger.warning(f"Invalid key attempted: {plain_key[:10]}...")
                return None
            
            product_key = ProductKey.from_dict(key_doc)
            
            # Check if active
            if not product_key.is_active:
                self.logger.warning(f"Inactive key attempted: {plain_key[:10]}...")
                return None
            
            # Check expiration
            if product_key.expires_at and product_key.expires_at < datetime.utcnow():
                self.logger.warning(f"Expired key attempted: {plain_key[:10]}...")
                return None
            
            return product_key
            
        except Exception as e:
            self.logger.error(f"Error validating key: {e}")
            return None
    
    def assign_key_to_user(self, plain_key: str, user_id: int, username: Optional[str] = None) -> bool:
        """
        Assign a product key to a Telegram user
        
        Args:
            plain_key: The plain text product key
            user_id: Telegram user ID
            username: Telegram username (optional)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            key_hash = self._hash_key(plain_key)
            
            update_data = {'user_id': user_id}
            if username:
                update_data['username'] = username
            
            result = self.keys_collection.update_one(
                {'key_hash': key_hash},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                self.logger.info(f"Assigned key to user_id={user_id}, username={username}")
                return True
            else:
                self.logger.warning(f"Failed to assign key - key not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Error assigning key: {e}")
            return False
    
    def revoke_key(self, plain_key: str) -> bool:
        """
        Revoke a product key

        Args:
            plain_key: The plain text product key

        Returns:
            True if successful, False otherwise
        """
        try:
            key_hash = self._hash_key(plain_key)

            result = self.keys_collection.update_one(
                {'key_hash': key_hash},
                {'$set': {'is_active': False}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Revoked key: {plain_key[:10]}...")
                return True
            else:
                self.logger.warning(f"Failed to revoke key - key not found")
                return False

        except Exception as e:
            self.logger.error(f"Error revoking key: {e}")
            return False

    def revoke_key_by_user_id(self, user_id: int) -> bool:
        """
        Revoke a product key by user ID

        Args:
            user_id: Telegram user ID

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.keys_collection.update_one(
                {'user_id': user_id},
                {'$set': {'is_active': False}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Revoked key for user_id={user_id}")
                return True
            else:
                self.logger.warning(f"Failed to revoke key - no key found for user_id={user_id}")
                return False

        except Exception as e:
            self.logger.error(f"Error revoking key by user_id: {e}")
            return False

    def revoke_key_by_username(self, username: str) -> bool:
        """
        Revoke a product key by username

        Args:
            username: Telegram username

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.keys_collection.update_one(
                {'username': username},
                {'$set': {'is_active': False}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Revoked key for username={username}")
                return True
            else:
                self.logger.warning(f"Failed to revoke key - no key found for username={username}")
                return False

        except Exception as e:
            self.logger.error(f"Error revoking key by username: {e}")
            return False

    def revoke_key_by_key_id(self, key_id: str) -> bool:
        """
        Revoke a product key by its MongoDB key ID

        Args:
            key_id: MongoDB ObjectId as string

        Returns:
            True if successful, False otherwise
        """
        try:
            from bson import ObjectId

            result = self.keys_collection.update_one(
                {'_id': ObjectId(key_id)},
                {'$set': {'is_active': False}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Revoked key with key_id={key_id}")
                return True
            else:
                self.logger.warning(f"Failed to revoke key - no key found with key_id={key_id}")
                return False

        except Exception as e:
            self.logger.error(f"Error revoking key by key_id: {e}")
            return False

    def get_key_by_user_id(self, user_id: int) -> Optional[ProductKey]:
        """
        Get product key by user ID (returns first match)

        Args:
            user_id: Telegram user ID

        Returns:
            ProductKey object if found, None otherwise
        """
        try:
            key_data = self.keys_collection.find_one({'user_id': user_id})
            if key_data:
                return ProductKey.from_dict(key_data)
            return None
        except Exception as e:
            self.logger.error(f"Error getting key by user_id: {e}")
            return None

    def get_all_keys_by_user_id(self, user_id: int) -> List[ProductKey]:
        """
        Get all product keys for a user ID (handles multiple keys per user)

        Args:
            user_id: Telegram user ID

        Returns:
            List of ProductKey objects
        """
        try:
            keys_data = self.keys_collection.find({'user_id': user_id})
            return [ProductKey.from_dict(key_data) for key_data in keys_data]
        except Exception as e:
            self.logger.error(f"Error getting keys by user_id: {e}")
            return []

    def get_all_keys_by_username(self, username: str) -> List[ProductKey]:
        """
        Get all product keys for a username (handles multiple keys per user)

        Args:
            username: Telegram username

        Returns:
            List of ProductKey objects
        """
        try:
            keys_data = self.keys_collection.find({'username': username})
            return [ProductKey.from_dict(key_data) for key_data in keys_data]
        except Exception as e:
            self.logger.error(f"Error getting keys by username: {e}")
            return []

    def delete_key_by_id(self, key_id: str) -> bool:
        """
        Permanently delete a product key by its ID

        Args:
            key_id: MongoDB ObjectId as string

        Returns:
            True if successful, False otherwise
        """
        try:
            from bson import ObjectId
            result = self.keys_collection.delete_one({'_id': ObjectId(key_id)})

            if result.deleted_count > 0:
                self.logger.info(f"Deleted key with ID: {key_id}")
                return True
            else:
                self.logger.warning(f"Failed to delete key - ID not found: {key_id}")
                return False

        except Exception as e:
            self.logger.error(f"Error deleting key by ID: {e}")
            return False

    def delete_keys_by_user_id(self, user_id: int) -> int:
        """
        Permanently delete all product keys for a user ID

        Args:
            user_id: Telegram user ID

        Returns:
            Number of keys deleted
        """
        try:
            result = self.keys_collection.delete_many({'user_id': user_id})
            count = result.deleted_count

            if count > 0:
                self.logger.info(f"Deleted {count} key(s) for user_id={user_id}")

            return count

        except Exception as e:
            self.logger.error(f"Error deleting keys by user_id: {e}")
            return 0

    def delete_keys_by_username(self, username: str) -> int:
        """
        Permanently delete all product keys for a username

        Args:
            username: Telegram username

        Returns:
            Number of keys deleted
        """
        try:
            result = self.keys_collection.delete_many({'username': username})
            count = result.deleted_count

            if count > 0:
                self.logger.info(f"Deleted {count} key(s) for username={username}")

            return count

        except Exception as e:
            self.logger.error(f"Error deleting keys by username: {e}")
            return 0
    
    def list_keys(self, active_only: bool = True) -> List[ProductKey]:
        """
        List all product keys
        
        Args:
            active_only: Only return active keys
        
        Returns:
            List of ProductKey objects
        """
        try:
            query = {}
            if active_only:
                query['is_active'] = True
            
            keys = []
            for doc in self.keys_collection.find(query):
                keys.append(ProductKey.from_dict(doc))
            
            return keys
            
        except Exception as e:
            self.logger.error(f"Error listing keys: {e}")
            return []
    
    def cleanup_expired_keys(self) -> int:
        """
        Deactivate expired keys
        
        Returns:
            Number of keys deactivated
        """
        try:
            result = self.keys_collection.update_many(
                {
                    'expires_at': {'$lt': datetime.utcnow()},
                    'is_active': True
                },
                {'$set': {'is_active': False}}
            )
            
            count = result.modified_count
            if count > 0:
                self.logger.info(f"Deactivated {count} expired keys")
            
            return count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up expired keys: {e}")
            return 0

