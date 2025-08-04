"""
User session management for News Tracker Bot
Handles temporary user state during conversations
"""

import time
from typing import Dict, Optional, Any
from ..utils.logging_config import get_logger


class UserSessionManager:
    """Manages user sessions for multi-step conversations"""
    
    def __init__(self, session_timeout: int = 300):  # 5 minutes
        self.sessions: Dict[int, Dict[str, Any]] = {}
        self.session_timeout = session_timeout
        self.logger = get_logger('sessions')
    
    def create_session(self, chat_id: int, source_name: str) -> Dict[str, Any]:
        """Create a new user session"""
        session = {
            'source_name': source_name,
            'created_at': time.time(),
            'last_activity': time.time()
        }
        
        self.sessions[chat_id] = session
        self.logger.debug(f"Created session for chat {chat_id}: {source_name}")
        
        return session
    
    def get_session(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get user session if it exists and is not expired"""
        if chat_id not in self.sessions:
            return None
        
        session = self.sessions[chat_id]
        
        # Check if session is expired
        if time.time() - session['last_activity'] > self.session_timeout:
            self.clear_session(chat_id)
            self.logger.debug(f"Session expired for chat {chat_id}")
            return None
        
        # Update last activity
        session['last_activity'] = time.time()
        return session
    
    def clear_session(self, chat_id: int) -> bool:
        """Clear user session"""
        if chat_id in self.sessions:
            del self.sessions[chat_id]
            self.logger.debug(f"Cleared session for chat {chat_id}")
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        current_time = time.time()
        expired_chats = []
        
        for chat_id, session in self.sessions.items():
            if current_time - session['last_activity'] > self.session_timeout:
                expired_chats.append(chat_id)
        
        for chat_id in expired_chats:
            del self.sessions[chat_id]
        
        if expired_chats:
            self.logger.info(f"Cleaned up {len(expired_chats)} expired sessions")
    
    def get_active_session_count(self) -> int:
        """Get number of active sessions"""
        self.cleanup_expired_sessions()
        return len(self.sessions)
    
    def get_session_info(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get session info for debugging"""
        session = self.get_session(chat_id)
        if not session:
            return None
        
        return {
            'source_name': session['source_name'],
            'created_at': session['created_at'],
            'last_activity': session['last_activity'],
            'age_seconds': time.time() - session['created_at']
        }
