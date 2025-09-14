"""
User Model

SQLAlchemy model for users table with platform-specific identifiers.
"""

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import List, Optional
from .base import Base

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    whatsapp_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    telegram_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    api_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    group_memberships: Mapped[List["GroupMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id='{self.id}', whatsapp_id='{self.whatsapp_id}', telegram_id='{self.telegram_id}')>"
    
    @property
    def platform_ids(self):
        """Get all platform IDs for this user."""
        return {
            "whatsapp": self.whatsapp_id,
            "telegram": self.telegram_id,
            "api": self.api_id
        }
    
    def get_platform_id(self, platform: str) -> str | None:
        """Get platform ID for specific platform."""
        return getattr(self, f"{platform}_id", None)