"""
Group Models

SQLAlchemy models for groups and group membership with role-based access.
"""

from sqlalchemy import String, DateTime, Boolean, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import List, Optional
from .base import Base
import enum


class GroupRole(enum.Enum):
    """Group role enumeration."""
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class Group(Base):
    __tablename__ = "groups"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    whatsapp_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    telegram_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    members: Mapped[List["GroupMember"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Group(id='{self.id}', name='{self.name}', active={self.is_active})>"
    
    @property
    def platform_ids(self):
        """Get all platform IDs for this group."""
        return {
            "whatsapp": self.whatsapp_id,
            "telegram": self.telegram_id
        }
    
    def get_platform_id(self, platform: str) -> str | None:
        """Get platform ID for specific platform."""
        return getattr(self, f"{platform}_id", None)
    
    @property
    def active_members_count(self):
        """Get count of active members (computed property)."""
        return len([m for m in self.members if m.left_at is None])


class GroupMember(Base):
    __tablename__ = "group_members"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    group_id: Mapped[str] = mapped_column(String, ForeignKey("groups.id", ondelete="CASCADE"))
    role: Mapped[GroupRole] = mapped_column(default=GroupRole.MEMBER)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="group_memberships")
    group: Mapped[Group] = relationship(back_populates="members")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="unique_user_group_membership"),
    )
    
    def __repr__(self):
        status = "active" if self.left_at is None else "left"
        return f"<GroupMember(user_id='{self.user_id}', group_id='{self.group_id}', role={self.role.value}, {status})>"
    
    @property
    def is_active(self):
        """Check if membership is currently active."""
        return self.left_at is None
    
    @property
    def is_admin(self):
        """Check if user is admin of this group."""
        return self.role == GroupRole.ADMIN and self.is_active