"""
AI Core Service Source Package

This package contains the core AI functionality for the multi-client chatbot.
"""

from .ai_service import AIService, get_ai_service
from .models import (
    ChatRequest,
    ChatResponse,
    UserCreateRequest,
    UserResponse,
    ConversationHistoryRequest,
    ConversationHistoryResponse,
    ConversationMessage,
    MessageSender,
    ErrorResponse,
    HealthResponse
)

__all__ = [
    "AIService",
    "get_ai_service",
    "ChatRequest",
    "ChatResponse", 
    "UserCreateRequest",
    "UserResponse",
    "ConversationHistoryRequest",
    "ConversationHistoryResponse",
    "ConversationMessage",
    "MessageSender",
    "ErrorResponse",
    "HealthResponse"
]