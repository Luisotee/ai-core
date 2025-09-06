"""
Database Module

This module provides database connection and session management utilities
for the AI core service to interact with the SQLite database via Prisma.
"""

import sqlite3
import os
import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Database manager for handling SQLite connections and operations.
    
    This class provides utilities for connecting to the SQLite database,
    managing user data, and storing conversation history.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize the database manager.
        
        Args:
            database_url: Database URL. If None, uses DATABASE_URL env var.
        """
        self.database_url = database_url or os.getenv("DATABASE_URL", "file:../prisma/dev.db")
        
        # Extract SQLite file path from database URL
        if self.database_url.startswith("file:"):
            self.db_path = self.database_url[5:]  # Remove "file:" prefix
        else:
            self.db_path = self.database_url
            
        logger.info(f"Database manager initialized with path: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable row access by column name
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def create_user(self, whatsapp_id: Optional[str] = None, telegram_id: Optional[str] = None, 
                   api_id: Optional[str] = None) -> Optional[str]:
        """
        Create a new user or find existing user by platform ID.
        
        Args:
            whatsapp_id: WhatsApp user identifier
            telegram_id: Telegram user identifier
            api_id: API client user identifier
            
        Returns:
            Optional[str]: User ID if successful, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, try to find existing user by any platform ID
                existing_user = self.find_user_by_platform_id(
                    whatsapp_id=whatsapp_id,
                    telegram_id=telegram_id,
                    api_id=api_id
                )
                
                if existing_user:
                    logger.info(f"Found existing user: {existing_user['id']}")
                    return existing_user['id']
                
                # Generate a simple user ID (in production, use proper CUID)
                import uuid
                user_id = str(uuid.uuid4())
                
                cursor.execute("""
                    INSERT INTO users (id, whatsapp_id, telegram_id, api_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
                """, (user_id, whatsapp_id, telegram_id, api_id))
                
                conn.commit()
                logger.info(f"Created new user: {user_id}")
                return user_id
                
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None
    
    def find_user_by_platform_id(self, whatsapp_id: Optional[str] = None, 
                                 telegram_id: Optional[str] = None, 
                                 api_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find user by any platform ID.
        
        Args:
            whatsapp_id: WhatsApp user identifier
            telegram_id: Telegram user identifier  
            api_id: API client user identifier
            
        Returns:
            Optional[Dict[str, Any]]: User data if found, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                conditions = []
                params = []
                
                if whatsapp_id:
                    conditions.append("whatsapp_id = ?")
                    params.append(whatsapp_id)
                if telegram_id:
                    conditions.append("telegram_id = ?")
                    params.append(telegram_id)
                if api_id:
                    conditions.append("api_id = ?")
                    params.append(api_id)
                
                if not conditions:
                    return None
                
                query = f"SELECT * FROM users WHERE {' OR '.join(conditions)}"
                cursor.execute(query, params)
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to find user: {e}")
            return None
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            Optional[Dict[str, Any]]: User data if found, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    def store_conversation(self, user_id: str, message: str, sender: str, 
                          context: Optional[str] = None) -> Optional[str]:
        """
        Store a conversation message.
        
        Args:
            user_id: User identifier
            message: Message content
            sender: Message sender ('USER' or 'AI')
            context: Optional conversation context
            
        Returns:
            Optional[str]: Message ID if successful, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                import uuid
                message_id = str(uuid.uuid4())
                
                cursor.execute("""
                    INSERT INTO conversations (id, user_id, message, sender, timestamp, context)
                    VALUES (?, ?, ?, ?, datetime('now'), ?)
                """, (message_id, user_id, message, sender, context))
                
                conn.commit()
                logger.debug(f"Stored conversation message: {message_id}")
                return message_id
                
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
            return None
    
    def get_conversation_history(self, user_id: str, limit: int = 50, 
                               offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get conversation history for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip
            
        Returns:
            List[Dict[str, Any]]: List of conversation messages
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM conversations 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get conversation history for {user_id}: {e}")
            return []
    
    def get_conversation_count(self, user_id: str) -> int:
        """
        Get total conversation count for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            int: Total message count
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,))
                
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except Exception as e:
            logger.error(f"Failed to get conversation count for {user_id}: {e}")
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a database health check.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Test basic connection
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
                # Check if tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('users', 'conversations')
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                # Get basic stats
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM conversations")
                message_count = cursor.fetchone()[0]
                
                return {
                    "status": "healthy",
                    "database_path": self.db_path,
                    "connection_test": "passed",
                    "tables_exist": tables,
                    "user_count": user_count,
                    "message_count": message_count
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "database_path": self.db_path,
                "connection_test": "failed",
                "error": str(e)
            }

# Global database manager instance
_db_manager_instance: Optional[DatabaseManager] = None

def get_database_manager() -> DatabaseManager:
    """
    Get or create the global database manager instance.
    
    Returns:
        DatabaseManager: The global database manager instance
    """
    global _db_manager_instance
    
    if _db_manager_instance is None:
        _db_manager_instance = DatabaseManager()
    
    return _db_manager_instance