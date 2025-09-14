"""
Conversation Model

SQLAlchemy model for conversations with group context separation support.
"""

from sqlalchemy import String, DateTime, ForeignKey, Text, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from .base import Base
import enum


class MessageSender(enum.Enum):
    """Message sender enumeration."""
    USER = "USER"
    AI = "AI"


class MessageType(enum.Enum):
    """Message type enumeration."""
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    DOCUMENT = "DOCUMENT"
    AUDIO = "AUDIO"
    SYSTEM = "SYSTEM"


class Platform(enum.Enum):
    """Platform enumeration."""
    WHATSAPP = "WHATSAPP"
    TELEGRAM = "TELEGRAM"
    API = "API"


class Conversation(Base):
    __tablename__ = "conversations"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(Text)
    sender: Mapped[MessageSender] = mapped_column()
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)
    context: Mapped[Optional[str]] = mapped_column(Text)
    message_type: Mapped[MessageType] = mapped_column(default=MessageType.TEXT)
    platform: Mapped[Optional[Platform]] = mapped_column()
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="conversations")
    group: Mapped[Optional["Group"]] = relationship(back_populates="conversations")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
        Index("idx_group_timestamp", "group_id", "timestamp"),
        Index("idx_platform_timestamp", "platform", "timestamp"),
    )
    
    def __repr__(self):
        context_type = "group" if self.group_id else "private"
        return f"<Conversation(id='{self.id}', {context_type}, sender={self.sender.value}, timestamp={self.timestamp})>"
    
    @property
    def is_private_conversation(self):
        """Check if this is a private conversation."""
        return self.group_id is None
    
    @property
    def is_group_conversation(self):
        """Check if this is a group conversation."""
        return self.group_id is not None
    
    @property
    def conversation_type(self):
        """Get conversation type as string."""
        return "private" if self.is_private_conversation else "group"