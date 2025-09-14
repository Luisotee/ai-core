"""
SQLAlchemy Models for AI Chatbot

This module contains all the SQLAlchemy models that replace the Prisma schema.
Models are designed to mirror the existing database structure while providing
proper Python typing and ORM capabilities.
"""

from .base import Base
from .user import User
from .group import Group, GroupMember, GroupRole
from .conversation import Conversation, MessageSender, MessageType, Platform

__all__ = [
    "Base",
    "User", 
    "Group",
    "GroupMember",
    "GroupRole",
    "Conversation",
    "MessageSender",
    "MessageType", 
    "Platform",
]