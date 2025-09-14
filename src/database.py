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
        self.database_url = database_url or os.getenv("DATABASE_URL", "file:data/dev.db")
        
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
                          context: Optional[str] = None, group_id: Optional[str] = None,
                          message_type: str = "TEXT", platform: Optional[str] = None) -> Optional[str]:
        """
        Store a conversation message with group context separation.
        
        Args:
            user_id: User identifier
            message: Message content
            sender: Message sender ('USER' or 'AI')
            context: Optional conversation context
            group_id: Group identifier (None for private conversations)
            message_type: Type of message ('TEXT', 'IMAGE', etc.)
            platform: Platform origin ('WHATSAPP', 'TELEGRAM', 'API')
            
        Returns:
            Optional[str]: Message ID if successful, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                import uuid
                message_id = str(uuid.uuid4())
                
                # Validate group membership if group_id is provided
                if group_id and not self.is_user_in_group(user_id, group_id):
                    logger.warning(f"User {user_id} not in group {group_id}, cannot store message")
                    return None
                
                cursor.execute("""
                    INSERT INTO conversations (id, user_id, group_id, message, sender, timestamp, context, messageType, platform)
                    VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?, ?)
                """, (message_id, user_id, group_id, message, sender, context, message_type, platform))
                
                conn.commit()
                
                context_type = "group" if group_id else "private"
                logger.debug(f"Stored {context_type} conversation message: {message_id}")
                return message_id
                
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
            return None
    
    def get_conversation_history(self, user_id: str, limit: int = 50, 
                               offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get PRIVATE conversation history for a user (excludes group messages).
        
        Args:
            user_id: User identifier
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip
            
        Returns:
            List[Dict[str, Any]]: List of private conversation messages
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM conversations 
                    WHERE user_id = ? AND group_id IS NULL
                    ORDER BY timestamp DESC 
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get private conversation history for {user_id}: {e}")
            return []
    
    def get_conversation_count(self, user_id: str, group_id: Optional[str] = None) -> int:
        """
        Get conversation count for a user in specific context.
        
        Args:
            user_id: User identifier
            group_id: Group identifier (None for private conversations)
            
        Returns:
            int: Message count in the specified context
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if group_id is None:
                    # Private conversations only
                    cursor.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ? AND group_id IS NULL", (user_id,))
                else:
                    # Specific group conversations
                    cursor.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ? AND group_id = ?", (user_id, group_id))
                
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except Exception as e:
            context = "private" if group_id is None else f"group {group_id}"
            logger.error(f"Failed to get {context} conversation count for {user_id}: {e}")
            return 0

    def get_group_conversation_history(self, group_id: str, limit: int = 50, 
                                     offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get conversation history for a specific group.
        
        Args:
            group_id: Group identifier
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip
            
        Returns:
            List[Dict[str, Any]]: List of group conversation messages with user info
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.*, u.whatsapp_id, u.telegram_id, u.api_id
                    FROM conversations c
                    JOIN users u ON c.user_id = u.id
                    WHERE c.group_id = ?
                    ORDER BY c.timestamp DESC 
                    LIMIT ? OFFSET ?
                """, (group_id, limit, offset))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get group conversation history for {group_id}: {e}")
            return []

    def get_group_conversation_count(self, group_id: str) -> int:
        """
        Get total conversation count for a group.
        
        Args:
            group_id: Group identifier
            
        Returns:
            int: Total message count in the group
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM conversations WHERE group_id = ?", (group_id,))
                
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except Exception as e:
            logger.error(f"Failed to get conversation count for group {group_id}: {e}")
            return 0

    def get_user_group_conversation_history(self, user_id: str, group_id: str, 
                                          limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get conversation history for a specific user in a specific group.
        
        Args:
            user_id: User identifier
            group_id: Group identifier
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip
            
        Returns:
            List[Dict[str, Any]]: List of user's messages in the group
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verify user is in group
                if not self.is_user_in_group(user_id, group_id):
                    logger.warning(f"User {user_id} not in group {group_id}")
                    return []
                
                cursor.execute("""
                    SELECT * FROM conversations 
                    WHERE user_id = ? AND group_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT ? OFFSET ?
                """, (user_id, group_id, limit, offset))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get conversation history for user {user_id} in group {group_id}: {e}")
            return []

    def get_conversation_context_for_ai(self, user_id: str, group_id: Optional[str] = None, 
                                      limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent conversation history for AI context with strict separation.
        
        Args:
            user_id: User identifier
            group_id: Group identifier (None for private context)
            limit: Maximum number of recent messages
            
        Returns:
            List[Dict[str, Any]]: Recent messages in chronological order for AI context
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if group_id is None:
                    # Private conversation context only
                    cursor.execute("""
                        SELECT * FROM conversations 
                        WHERE user_id = ? AND group_id IS NULL
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (user_id, limit))
                else:
                    # Group conversation context only - verify membership
                    if not self.is_user_in_group(user_id, group_id):
                        logger.warning(f"User {user_id} not in group {group_id}")
                        return []
                    
                    cursor.execute("""
                        SELECT * FROM conversations 
                        WHERE group_id = ?
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (group_id, limit))
                
                rows = cursor.fetchall()
                # Return in chronological order (oldest first) for AI context
                return [dict(row) for row in reversed(rows)]
                
        except Exception as e:
            context_type = "private" if group_id is None else f"group {group_id}"
            logger.error(f"Failed to get {context_type} context for user {user_id}: {e}")
            return []

    def get_group_conversation_by_date_range(self, group_id: str, start_date: str, 
                                           end_date: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get group conversation history within a specific date range.
        
        Args:
            group_id: Group identifier
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            limit: Maximum number of messages to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of group messages in date range
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.*, u.whatsapp_id, u.telegram_id, u.api_id
                    FROM conversations c
                    JOIN users u ON c.user_id = u.id
                    WHERE c.group_id = ? 
                    AND DATE(c.timestamp) BETWEEN DATE(?) AND DATE(?)
                    ORDER BY c.timestamp ASC
                    LIMIT ?
                """, (group_id, start_date, end_date, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get group conversation by date range for {group_id}: {e}")
            return []

    def get_group_conversation_by_user(self, group_id: str, user_id: str, 
                                     limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all messages from a specific user in a group.
        
        Args:
            group_id: Group identifier
            user_id: User identifier
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip
            
        Returns:
            List[Dict[str, Any]]: List of user's messages in the group
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verify user is/was in group
                membership = self.get_group_membership(user_id, group_id)
                if not membership:
                    logger.warning(f"User {user_id} has no membership record for group {group_id}")
                    return []
                
                cursor.execute("""
                    SELECT c.*, u.whatsapp_id, u.telegram_id, u.api_id
                    FROM conversations c
                    JOIN users u ON c.user_id = u.id
                    WHERE c.group_id = ? AND c.user_id = ?
                    ORDER BY c.timestamp DESC
                    LIMIT ? OFFSET ?
                """, (group_id, user_id, limit, offset))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get group conversation by user {user_id} in group {group_id}: {e}")
            return []

    def get_group_conversation_by_message_type(self, group_id: str, message_type: str, 
                                             limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get group messages filtered by message type.
        
        Args:
            group_id: Group identifier
            message_type: Message type to filter ('TEXT', 'IMAGE', 'SYSTEM', etc.)
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip
            
        Returns:
            List[Dict[str, Any]]: List of filtered group messages
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.*, u.whatsapp_id, u.telegram_id, u.api_id
                    FROM conversations c
                    JOIN users u ON c.user_id = u.id
                    WHERE c.group_id = ? AND c.messageType = ?
                    ORDER BY c.timestamp DESC
                    LIMIT ? OFFSET ?
                """, (group_id, message_type, limit, offset))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get group conversation by message type {message_type} in group {group_id}: {e}")
            return []

    def search_group_conversations(self, group_id: str, search_term: str, 
                                 limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for messages containing specific text within a group.
        
        Args:
            group_id: Group identifier
            search_term: Text to search for in messages
            limit: Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of matching group messages
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                search_pattern = f"%{search_term}%"
                cursor.execute("""
                    SELECT c.*, u.whatsapp_id, u.telegram_id, u.api_id
                    FROM conversations c
                    JOIN users u ON c.user_id = u.id
                    WHERE c.group_id = ? AND c.message LIKE ?
                    ORDER BY c.timestamp DESC
                    LIMIT ?
                """, (group_id, search_pattern, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to search group conversations for '{search_term}' in group {group_id}: {e}")
            return []

    def get_group_activity_summary(self, group_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get activity summary for a group over the specified number of days.
        
        Args:
            group_id: Group identifier
            days: Number of days to analyze
            
        Returns:
            Dict[str, Any]: Activity summary with statistics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total messages in period
                cursor.execute("""
                    SELECT COUNT(*) FROM conversations 
                    WHERE group_id = ? AND timestamp >= datetime('now', '-{} days')
                """.format(days), (group_id,))
                total_messages = cursor.fetchone()[0]
                
                # Active users in period
                cursor.execute("""
                    SELECT COUNT(DISTINCT user_id) FROM conversations 
                    WHERE group_id = ? AND timestamp >= datetime('now', '-{} days')
                """.format(days), (group_id,))
                active_users = cursor.fetchone()[0]
                
                # Most active user in period
                cursor.execute("""
                    SELECT u.whatsapp_id, u.telegram_id, u.api_id, COUNT(*) as message_count
                    FROM conversations c
                    JOIN users u ON c.user_id = u.id
                    WHERE c.group_id = ? AND c.timestamp >= datetime('now', '-{} days')
                    GROUP BY c.user_id
                    ORDER BY message_count DESC
                    LIMIT 1
                """.format(days), (group_id,))
                most_active = cursor.fetchone()
                most_active_user = dict(most_active) if most_active else None
                
                # Message types breakdown
                cursor.execute("""
                    SELECT messageType, COUNT(*) as count
                    FROM conversations 
                    WHERE group_id = ? AND timestamp >= datetime('now', '-{} days')
                    GROUP BY messageType
                """.format(days), (group_id,))
                message_types = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Daily activity
                cursor.execute("""
                    SELECT DATE(timestamp) as date, COUNT(*) as count
                    FROM conversations 
                    WHERE group_id = ? AND timestamp >= datetime('now', '-{} days')
                    GROUP BY DATE(timestamp)
                    ORDER BY date DESC
                """.format(days), (group_id,))
                daily_activity = [{"date": row[0], "message_count": row[1]} for row in cursor.fetchall()]
                
                return {
                    "group_id": group_id,
                    "period_days": days,
                    "total_messages": total_messages,
                    "active_users": active_users,
                    "most_active_user": most_active_user,
                    "message_types": message_types,
                    "daily_activity": daily_activity
                }
                
        except Exception as e:
            logger.error(f"Failed to get activity summary for group {group_id}: {e}")
            return {}

    def get_all_group_conversations_for_user(self, user_id: str, limit: int = 50, 
                                           offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get conversation history across ALL groups a user belongs to.
        
        Args:
            user_id: User identifier
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip
            
        Returns:
            List[Dict[str, Any]]: List of group messages with group info
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.*, g.name as group_name, g.whatsapp_id as group_whatsapp_id, 
                           g.telegram_id as group_telegram_id
                    FROM conversations c
                    JOIN groups g ON c.group_id = g.id
                    JOIN group_members gm ON g.id = gm.group_id
                    WHERE gm.user_id = ? AND gm.left_at IS NULL AND g.isActive = 1
                    ORDER BY c.timestamp DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get all group conversations for user {user_id}: {e}")
            return []
    
    def update_user_platform_id(self, user_id: str, platform: str, platform_id: str) -> bool:
        """
        Update or add a platform ID for an existing user.
        
        Args:
            user_id: User identifier
            platform: Platform name ('whatsapp', 'telegram', 'api')
            platform_id: Platform-specific user identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Map platform names to column names
                platform_columns = {
                    'whatsapp': 'whatsapp_id',
                    'telegram': 'telegram_id',
                    'api': 'api_id'
                }
                
                if platform not in platform_columns:
                    logger.error(f"Invalid platform: {platform}")
                    return False
                
                column_name = platform_columns[platform]
                query = f"UPDATE users SET {column_name} = ?, updated_at = datetime('now') WHERE id = ?"
                cursor.execute(query, (platform_id, user_id))
                
                conn.commit()
                logger.info(f"Updated {platform} ID for user {user_id}")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to update user platform ID: {e}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user and all associated conversations.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete user (conversations will be cascade deleted due to foreign key)
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                
                conn.commit()
                logger.info(f"Deleted user: {user_id}")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False
    
    def get_recent_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent conversations across all users.
        
        Args:
            limit: Maximum number of conversations to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of recent conversations with user info
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.*, u.whatsapp_id, u.telegram_id, u.api_id 
                    FROM conversations c
                    JOIN users u ON c.user_id = u.id
                    ORDER BY c.timestamp DESC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get recent conversations: {e}")
            return []
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about users and conversations.
        
        Returns:
            Dict[str, Any]: Statistics about the database
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Basic counts
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM conversations")
                total_messages = cursor.fetchone()[0]
                
                # Platform-specific counts
                cursor.execute("SELECT COUNT(*) FROM users WHERE whatsapp_id IS NOT NULL")
                whatsapp_users = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM users WHERE telegram_id IS NOT NULL")
                telegram_users = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM users WHERE api_id IS NOT NULL")
                api_users = cursor.fetchone()[0]
                
                # Message type counts
                cursor.execute("SELECT COUNT(*) FROM conversations WHERE sender = 'USER'")
                user_messages = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM conversations WHERE sender = 'AI'")
                ai_messages = cursor.fetchone()[0]
                
                # Most active user
                cursor.execute("""
                    SELECT user_id, COUNT(*) as message_count
                    FROM conversations
                    GROUP BY user_id
                    ORDER BY message_count DESC
                    LIMIT 1
                """)
                most_active = cursor.fetchone()
                most_active_user = dict(most_active) if most_active else None
                
                return {
                    "total_users": total_users,
                    "total_messages": total_messages,
                    "platform_users": {
                        "whatsapp": whatsapp_users,
                        "telegram": telegram_users,
                        "api": api_users
                    },
                    "message_types": {
                        "user_messages": user_messages,
                        "ai_messages": ai_messages
                    },
                    "most_active_user": most_active_user
                }
                
        except Exception as e:
            logger.error(f"Failed to get user statistics: {e}")
            return {}
    
    def cleanup_old_conversations(self, days_old: int = 30) -> int:
        """
        Clean up conversations older than specified days.
        
        Args:
            days_old: Number of days old to consider for cleanup
            
        Returns:
            int: Number of conversations deleted
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM conversations 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days_old))
                
                deleted_count = cursor.rowcount
                conn.commit()
                logger.info(f"Cleaned up {deleted_count} old conversations")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old conversations: {e}")
            return 0

    def create_group(self, whatsapp_id: Optional[str] = None, telegram_id: Optional[str] = None,
                    name: Optional[str] = None, description: Optional[str] = None) -> Optional[str]:
        """
        Create a new group or find existing group by platform ID.
        
        Args:
            whatsapp_id: WhatsApp group identifier
            telegram_id: Telegram group identifier
            name: Group name/title
            description: Group description
            
        Returns:
            Optional[str]: Group ID if successful, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, try to find existing group by any platform ID
                existing_group = self.find_group_by_platform_id(
                    whatsapp_id=whatsapp_id,
                    telegram_id=telegram_id
                )
                
                if existing_group:
                    logger.info(f"Found existing group: {existing_group['id']}")
                    return existing_group['id']
                
                # Generate a simple group ID (in production, use proper CUID)
                import uuid
                group_id = str(uuid.uuid4())
                
                cursor.execute("""
                    INSERT INTO groups (id, whatsapp_id, telegram_id, name, description, isActive, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """, (group_id, whatsapp_id, telegram_id, name, description, True))
                
                conn.commit()
                logger.info(f"Created new group: {group_id}")
                return group_id
                
        except Exception as e:
            logger.error(f"Failed to create group: {e}")
            return None

    def find_group_by_platform_id(self, whatsapp_id: Optional[str] = None,
                                 telegram_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find group by any platform ID.
        
        Args:
            whatsapp_id: WhatsApp group identifier
            telegram_id: Telegram group identifier
            
        Returns:
            Optional[Dict[str, Any]]: Group data if found, None otherwise
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
                
                if not conditions:
                    return None
                
                query = f"SELECT * FROM groups WHERE {' OR '.join(conditions)} AND isActive = 1"
                cursor.execute(query, params)
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to find group: {e}")
            return None

    def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Get group by ID.
        
        Args:
            group_id: Group identifier
            
        Returns:
            Optional[Dict[str, Any]]: Group data if found, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM groups WHERE id = ? AND isActive = 1", (group_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get group {group_id}: {e}")
            return None

    def update_group(self, group_id: str, name: Optional[str] = None, 
                    description: Optional[str] = None) -> bool:
        """
        Update group information.
        
        Args:
            group_id: Group identifier
            name: New group name
            description: New group description
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                if description is not None:
                    updates.append("description = ?")
                    params.append(description)
                
                if not updates:
                    return True  # Nothing to update
                
                updates.append("updated_at = datetime('now')")
                params.append(group_id)
                
                query = f"UPDATE groups SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                
                conn.commit()
                logger.info(f"Updated group: {group_id}")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to update group {group_id}: {e}")
            return False

    def deactivate_group(self, group_id: str) -> bool:
        """
        Deactivate a group (soft delete).
        
        Args:
            group_id: Group identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE groups 
                    SET isActive = 0, updated_at = datetime('now') 
                    WHERE id = ?
                """, (group_id,))
                
                conn.commit()
                logger.info(f"Deactivated group: {group_id}")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to deactivate group {group_id}: {e}")
            return False

    def get_user_groups(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active groups a user belongs to.
        
        Args:
            user_id: User identifier
            
        Returns:
            List[Dict[str, Any]]: List of groups with membership info
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT g.*, gm.role, gm.joined_at, gm.left_at
                    FROM groups g
                    JOIN group_members gm ON g.id = gm.group_id
                    WHERE gm.user_id = ? AND g.isActive = 1 AND gm.left_at IS NULL
                    ORDER BY gm.joined_at DESC
                """, (user_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get groups for user {user_id}: {e}")
            return []

    def add_user_to_group(self, user_id: str, group_id: str, role: str = "MEMBER") -> Optional[str]:
        """
        Add a user to a group with specified role.
        
        Args:
            user_id: User identifier
            group_id: Group identifier
            role: User role in group ("ADMIN" or "MEMBER")
            
        Returns:
            Optional[str]: Membership ID if successful, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if user is already in the group
                existing_membership = self.get_group_membership(user_id, group_id)
                if existing_membership and existing_membership.get('left_at') is None:
                    logger.info(f"User {user_id} already in group {group_id}")
                    return existing_membership['id']
                
                # If user left the group before, reactivate membership
                if existing_membership and existing_membership.get('left_at') is not None:
                    cursor.execute("""
                        UPDATE group_members 
                        SET left_at = NULL, role = ?, joined_at = datetime('now')
                        WHERE user_id = ? AND group_id = ?
                    """, (role, user_id, group_id))
                    conn.commit()
                    logger.info(f"Reactivated user {user_id} in group {group_id}")
                    return existing_membership['id']
                
                # Create new membership
                import uuid
                membership_id = str(uuid.uuid4())
                
                cursor.execute("""
                    INSERT INTO group_members (id, user_id, group_id, role, joined_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                """, (membership_id, user_id, group_id, role))
                
                conn.commit()
                logger.info(f"Added user {user_id} to group {group_id} as {role}")
                return membership_id
                
        except Exception as e:
            logger.error(f"Failed to add user {user_id} to group {group_id}: {e}")
            return None

    def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """
        Remove a user from a group (mark as left).
        
        Args:
            user_id: User identifier
            group_id: Group identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE group_members 
                    SET left_at = datetime('now')
                    WHERE user_id = ? AND group_id = ? AND left_at IS NULL
                """, (user_id, group_id))
                
                conn.commit()
                if cursor.rowcount > 0:
                    logger.info(f"Removed user {user_id} from group {group_id}")
                    return True
                else:
                    logger.warning(f"User {user_id} not found in group {group_id}")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to remove user {user_id} from group {group_id}: {e}")
            return False

    def update_user_group_role(self, user_id: str, group_id: str, role: str) -> bool:
        """
        Update a user's role in a group.
        
        Args:
            user_id: User identifier
            group_id: Group identifier
            role: New role ("ADMIN" or "MEMBER")
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if role not in ["ADMIN", "MEMBER"]:
                    logger.error(f"Invalid role: {role}")
                    return False
                
                cursor.execute("""
                    UPDATE group_members 
                    SET role = ?
                    WHERE user_id = ? AND group_id = ? AND left_at IS NULL
                """, (role, user_id, group_id))
                
                conn.commit()
                if cursor.rowcount > 0:
                    logger.info(f"Updated user {user_id} role to {role} in group {group_id}")
                    return True
                else:
                    logger.warning(f"User {user_id} not found in group {group_id}")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to update user {user_id} role in group {group_id}: {e}")
            return False

    def get_group_membership(self, user_id: str, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific group membership record.
        
        Args:
            user_id: User identifier
            group_id: Group identifier
            
        Returns:
            Optional[Dict[str, Any]]: Membership data if found, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM group_members 
                    WHERE user_id = ? AND group_id = ?
                    ORDER BY joined_at DESC
                    LIMIT 1
                """, (user_id, group_id))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get membership for user {user_id} in group {group_id}: {e}")
            return None

    def get_group_members(self, group_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all members of a group.
        
        Args:
            group_id: Group identifier
            active_only: If True, only return active members
            
        Returns:
            List[Dict[str, Any]]: List of members with user info
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                where_clause = "WHERE gm.group_id = ?"
                params = [group_id]
                
                if active_only:
                    where_clause += " AND gm.left_at IS NULL"
                
                cursor.execute(f"""
                    SELECT u.*, gm.role, gm.joined_at, gm.left_at
                    FROM users u
                    JOIN group_members gm ON u.id = gm.user_id
                    {where_clause}
                    ORDER BY gm.joined_at ASC
                """, params)
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get members for group {group_id}: {e}")
            return []

    def get_group_admins(self, group_id: str) -> List[Dict[str, Any]]:
        """
        Get all admin members of a group.
        
        Args:
            group_id: Group identifier
            
        Returns:
            List[Dict[str, Any]]: List of admin members
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT u.*, gm.role, gm.joined_at
                    FROM users u
                    JOIN group_members gm ON u.id = gm.user_id
                    WHERE gm.group_id = ? AND gm.role = 'ADMIN' AND gm.left_at IS NULL
                    ORDER BY gm.joined_at ASC
                """, (group_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get admins for group {group_id}: {e}")
            return []

    def is_user_in_group(self, user_id: str, group_id: str) -> bool:
        """
        Check if a user is currently in a group.
        
        Args:
            user_id: User identifier
            group_id: Group identifier
            
        Returns:
            bool: True if user is in group, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM group_members 
                    WHERE user_id = ? AND group_id = ? AND left_at IS NULL
                """, (user_id, group_id))
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Failed to check if user {user_id} is in group {group_id}: {e}")
            return False

    def is_user_group_admin(self, user_id: str, group_id: str) -> bool:
        """
        Check if a user is an admin of a group.
        
        Args:
            user_id: User identifier
            group_id: Group identifier
            
        Returns:
            bool: True if user is admin, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM group_members 
                    WHERE user_id = ? AND group_id = ? AND role = 'ADMIN' AND left_at IS NULL
                """, (user_id, group_id))
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Failed to check if user {user_id} is admin of group {group_id}: {e}")
            return False

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