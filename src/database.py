"""
Database connection utilities for AI Core service.
Provides connection to SQLite database through HTTP requests to Node.js/Prisma API.
"""

import os
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseClient:
    """Client for database operations via HTTP API."""
    
    def __init__(self, api_base_url: Optional[str] = None):
        self.api_base_url = api_base_url or os.getenv("AI_CORE_URL", "http://localhost:8000")
        self.client = httpx.AsyncClient()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def create_user(self, platform_id: str, platform_type: str) -> Dict[str, Any]:
        """
        Create or get existing user by platform ID.
        
        Args:
            platform_id: The platform-specific user ID
            platform_type: Platform type ('whatsapp', 'telegram', 'api')
        
        Returns:
            User data dictionary
        """
        try:
            response = await self.client.post(
                f"{self.api_base_url}/api/v1/users",
                json={
                    "platform_id": platform_id,
                    "platform_type": platform_type
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create/get user: {e}")
            raise
    
    async def get_user_by_platform(self, platform_id: str, platform_type: str) -> Optional[Dict[str, Any]]:
        """
        Get user by platform ID and type.
        
        Args:
            platform_id: The platform-specific user ID
            platform_type: Platform type ('whatsapp', 'telegram', 'api')
        
        Returns:
            User data dictionary or None if not found
        """
        try:
            response = await self.client.get(
                f"{self.api_base_url}/api/v1/users/by-platform",
                params={
                    "platform_id": platform_id,
                    "platform_type": platform_type
                }
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get user by platform: {e}")
            raise
    
    async def save_conversation(
        self,
        user_id: str,
        message: str,
        sender: str,  # 'USER' or 'AI'
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save a conversation message to the database.
        
        Args:
            user_id: The user's UUID
            message: The message content
            sender: Either 'USER' or 'AI'
            context: Optional conversation context
        
        Returns:
            Conversation record dictionary
        """
        try:
            response = await self.client.post(
                f"{self.api_base_url}/api/v1/conversations",
                json={
                    "user_id": user_id,
                    "message": message,
                    "sender": sender,
                    "context": context
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            raise
    
    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a user.
        
        Args:
            user_id: The user's UUID
            limit: Maximum number of messages to retrieve
        
        Returns:
            List of conversation records
        """
        try:
            response = await self.client.get(
                f"{self.api_base_url}/api/v1/users/{user_id}/history",
                params={"limit": limit}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            raise


# Global database client instance
db_client: Optional[DatabaseClient] = None


async def get_db_client() -> DatabaseClient:
    """Get the global database client instance."""
    global db_client
    if db_client is None:
        db_client = DatabaseClient()
    return db_client


async def close_db_client():
    """Close the global database client."""
    global db_client
    if db_client:
        await db_client.close()
        db_client = None