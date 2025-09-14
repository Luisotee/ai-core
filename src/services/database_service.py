"""
Database Service using SQLAlchemy ORM

This service provides async database operations using SQLAlchemy with proper async patterns.
Replaces the raw SQL implementation with clean ORM methods.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import uuid

from ..models import (
    User, Group, GroupMember, GroupRole, Conversation, 
    MessageSender, MessageType, Platform
)
from ..models.base import AsyncSessionLocal, async_engine

logger = logging.getLogger(__name__)

class DatabaseService:
    """
    Async database service using SQLAlchemy ORM.
    
    Provides clean, typed methods for all database operations with proper
    async patterns and session management.
    """
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            async with AsyncSessionLocal() as session:
                # Simple query to test database connectivity
                result = await session.execute(select(func.count()).select_from(User))
                user_count = result.scalar()
                
                return {
                    "status": "healthy",
                    "database": "sqlite",
                    "user_count": user_count,
                    "connection": "active"
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy", 
                "error": str(e),
                "database": "sqlite"
            }
    
    # User Management
    async def create_user(
        self,
        whatsapp_id: Optional[str] = None,
        telegram_id: Optional[str] = None,
        api_id: Optional[str] = None
    ) -> User:
        """Create a new user"""
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            whatsapp_id=whatsapp_id,
            telegram_id=telegram_id,
            api_id=api_id
        )
        
        async with AsyncSessionLocal() as session:
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
    
    async def get_user_by_platform_id(
        self, 
        platform: str, 
        platform_id: str
    ) -> Optional[User]:
        """Get user by platform-specific ID"""
        column_map = {
            "whatsapp": User.whatsapp_id,
            "telegram": User.telegram_id,
            "api": User.api_id
        }
        
        if platform not in column_map:
            raise ValueError(f"Invalid platform: {platform}")
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(column_map[platform] == platform_id)
            )
            return result.scalar_one_or_none()
    
    async def find_or_create_user(
        self,
        whatsapp_id: Optional[str] = None,
        telegram_id: Optional[str] = None,
        api_id: Optional[str] = None
    ) -> User:
        """Find existing user or create new one"""
        # Try to find existing user
        user = None
        if whatsapp_id:
            user = await self.get_user_by_platform_id("whatsapp", whatsapp_id)
        elif telegram_id:
            user = await self.get_user_by_platform_id("telegram", telegram_id)
        elif api_id:
            user = await self.get_user_by_platform_id("api", api_id)
        
        if user:
            return user
        
        # Create new user
        return await self.create_user(
            whatsapp_id=whatsapp_id,
            telegram_id=telegram_id,
            api_id=api_id
        )
    
    # Group Management
    async def create_group(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        whatsapp_id: Optional[str] = None,
        telegram_id: Optional[str] = None
    ) -> Group:
        """Create a new group"""
        group_id = str(uuid.uuid4())
        group = Group(
            id=group_id,
            name=name,
            description=description,
            whatsapp_id=whatsapp_id,
            telegram_id=telegram_id,
            is_active=True
        )
        
        async with AsyncSessionLocal() as session:
            session.add(group)
            await session.commit()
            await session.refresh(group)
            return group
    
    async def get_group_by_id(self, group_id: str) -> Optional[Group]:
        """Get group by ID"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Group).where(Group.id == group_id))
            return result.scalar_one_or_none()
    
    async def get_group_by_platform_id(
        self, 
        platform: str, 
        platform_id: str
    ) -> Optional[Group]:
        """Get group by platform-specific ID"""
        column_map = {
            "whatsapp": Group.whatsapp_id,
            "telegram": Group.telegram_id
        }
        
        if platform not in column_map:
            raise ValueError(f"Invalid platform: {platform}")
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Group).where(column_map[platform] == platform_id)
            )
            return result.scalar_one_or_none()
    
    async def find_or_create_group(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        whatsapp_id: Optional[str] = None,
        telegram_id: Optional[str] = None
    ) -> Group:
        """Find existing group or create new one"""
        # Try to find existing group
        group = None
        if whatsapp_id:
            group = await self.get_group_by_platform_id("whatsapp", whatsapp_id)
        elif telegram_id:
            group = await self.get_group_by_platform_id("telegram", telegram_id)
        
        if group:
            return group
        
        # Create new group
        return await self.create_group(
            name=name,
            description=description,
            whatsapp_id=whatsapp_id,
            telegram_id=telegram_id
        )
    
    # Group Membership Management
    async def add_user_to_group(
        self,
        user_id: str,
        group_id: str,
        role: GroupRole = GroupRole.MEMBER
    ) -> GroupMember:
        """Add user to group"""
        membership_id = str(uuid.uuid4())
        membership = GroupMember(
            id=membership_id,
            user_id=user_id,
            group_id=group_id,
            role=role
        )
        
        async with AsyncSessionLocal() as session:
            session.add(membership)
            await session.commit()
            await session.refresh(membership)
            return membership
    
    async def get_group_membership(
        self, 
        user_id: str, 
        group_id: str
    ) -> Optional[GroupMember]:
        """Get group membership for user"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(GroupMember).where(
                    and_(
                        GroupMember.user_id == user_id,
                        GroupMember.group_id == group_id,
                        GroupMember.left_at.is_(None)
                    )
                )
            )
            return result.scalar_one_or_none()
    
    async def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """Remove user from group (mark as left)"""
        async with AsyncSessionLocal() as session:
            membership = await session.execute(
                select(GroupMember).where(
                    and_(
                        GroupMember.user_id == user_id,
                        GroupMember.group_id == group_id,
                        GroupMember.left_at.is_(None)
                    )
                )
            )
            membership = membership.scalar_one_or_none()
            
            if membership:
                membership.left_at = datetime.utcnow()
                await session.commit()
                return True
            return False
    
    # Conversation Management
    async def add_conversation(
        self,
        user_id: str,
        message: str,
        sender: MessageSender,
        group_id: Optional[str] = None,
        platform: Optional[Platform] = None,
        message_type: MessageType = MessageType.TEXT,
        context: Optional[str] = None
    ) -> Conversation:
        """Add a new conversation message"""
        conversation_id = str(uuid.uuid4())
        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            group_id=group_id,
            message=message,
            sender=sender,
            platform=platform,
            message_type=message_type,
            context=context
        )
        
        async with AsyncSessionLocal() as session:
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            return conversation
    
    async def get_conversation_history(
        self,
        user_id: str,
        group_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Conversation]:
        """Get conversation history with proper context separation"""
        async with AsyncSessionLocal() as session:
            query = select(Conversation).where(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.group_id == group_id  # This handles both None and specific group_id
                )
            ).order_by(desc(Conversation.timestamp)).limit(limit)
            
            result = await session.execute(query)
            conversations = result.scalars().all()
            return list(reversed(conversations))  # Return in chronological order
    
    async def get_recent_conversations(
        self,
        user_id: str,
        group_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Conversation]:
        """Get recent conversations within specified hours"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        async with AsyncSessionLocal() as session:
            query = select(Conversation).where(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.group_id == group_id,
                    Conversation.timestamp >= since
                )
            ).order_by(desc(Conversation.timestamp))
            
            result = await session.execute(query)
            conversations = result.scalars().all()
            return list(reversed(conversations))
    
    async def get_conversation_context_for_ai(
        self,
        user_id: str,
        group_id: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """
        Get formatted conversation context for AI with proper group/private separation.
        
        CRITICAL: This ensures group and private conversations never mix!
        """
        conversations = await self.get_conversation_history(
            user_id=user_id,
            group_id=group_id,  # This maintains strict separation
            limit=limit
        )
        
        if not conversations:
            context_type = "group chat" if group_id else "private chat"
            return f"This is the beginning of your {context_type} conversation."
        
        context_lines = []
        for conv in conversations:
            sender_label = "User" if conv.sender == MessageSender.USER else "AI"
            context_lines.append(f"{sender_label}: {conv.message}")
        
        context_type = "group" if group_id else "private"
        return f"Recent {context_type} conversation:\n" + "\n".join(context_lines)
    
    async def get_group_conversation_history(
        self,
        group_id: str,
        limit: int = 50
    ) -> List[Conversation]:
        """Get conversation history for a specific group (all users in the group)"""
        async with AsyncSessionLocal() as session:
            query = select(Conversation).where(
                Conversation.group_id == group_id
            ).order_by(desc(Conversation.timestamp)).limit(limit)
            
            result = await session.execute(query)
            conversations = result.scalars().all()
            return list(reversed(conversations))  # Return in chronological order


# Global database service instance
_database_service_instance: Optional[DatabaseService] = None

def get_database_service() -> DatabaseService:
    """Get or create the global database service instance"""
    global _database_service_instance
    
    if _database_service_instance is None:
        _database_service_instance = DatabaseService()
    
    return _database_service_instance