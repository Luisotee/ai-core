"""
Pydantic Models for API Communication

This module defines the request and response models used for API communication
between client applications and the AI core service.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
import re

class MessageSender(str, Enum):
    """Enum for message sender types"""
    USER = "USER"
    AI = "AI"

class Platform(str, Enum):
    """Enum for platform types"""
    WHATSAPP = "WHATSAPP"
    TELEGRAM = "TELEGRAM"
    API = "API"

class ChatRequest(BaseModel):
    """
    Request model for chat/query endpoints.
    
    This model represents a user's request to the AI service with group support.
    """
    message: str = Field(..., min_length=1, max_length=10000, description="The user's message or query")
    
    # User identification (at least one platform ID required)
    whatsapp_id: Optional[str] = Field(None, description="WhatsApp user identifier")
    telegram_id: Optional[str] = Field(None, description="Telegram user identifier") 
    api_id: Optional[str] = Field(None, description="API client user identifier")
    
    # Group context (optional - if provided, this is a group message)
    group_whatsapp_id: Optional[str] = Field(None, description="WhatsApp group identifier")
    group_telegram_id: Optional[str] = Field(None, description="Telegram group identifier")
    group_name: Optional[str] = Field(None, description="Group name/title")
    
    # Platform and context
    platform: Optional[Platform] = Field(None, description="Platform where the message originated")
    context: Optional[str] = Field(None, max_length=5000, description="Optional conversation context")
    
    @validator('whatsapp_id')
    def validate_whatsapp_id(cls, v):
        if v is not None and not re.match(r'^\d+@[cg]\.us$', v):
            raise ValueError('WhatsApp ID must be in format: digits@c.us or digits@g.us')
        return v
    
    @validator('telegram_id')
    def validate_telegram_id(cls, v):
        if v is not None and not v.isdigit():
            raise ValueError('Telegram ID must be numeric')
        return v
    
    @validator('group_whatsapp_id')
    def validate_group_whatsapp_id(cls, v):
        if v is not None and not re.match(r'^\d+@g\.us$', v):
            raise ValueError('WhatsApp Group ID must be in format: digits@g.us')
        return v
    
    @validator('group_telegram_id')
    def validate_group_telegram_id(cls, v):
        if v is not None and not (v.startswith('-') and v[1:].isdigit()):
            raise ValueError('Telegram Group ID must be negative numeric (e.g., -123456789)')
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "What is the capital of France?",
                    "whatsapp_id": "1234567890@c.us",
                    "platform": "WHATSAPP",
                    "context": "We were discussing European capitals"
                },
                {
                    "message": "Hello everyone!",
                    "whatsapp_id": "1234567890@c.us", 
                    "group_whatsapp_id": "120363025343298878@g.us",
                    "group_name": "Study Group",
                    "platform": "WHATSAPP"
                }
            ]
        }
    }

class ChatResponse(BaseModel):
    """
    Response model for chat/query endpoints.
    
    This model represents the AI service's response to a user query with group context.
    """
    response: str = Field(..., description="The AI-generated response")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Response timestamp")
    user_id: str = Field(..., description="User identifier")
    group_id: Optional[str] = Field(None, description="Group identifier if this was a group message")
    conversation_type: str = Field(..., description="Type of conversation: 'private' or 'group'")
    processing_time_ms: Optional[float] = Field(None, description="Time taken to process the request in milliseconds")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "The capital of France is Paris.",
                    "timestamp": "2024-09-06T17:00:00Z",
                    "user_id": "clm7x8y9z0000abc123def456",
                    "group_id": None,
                    "conversation_type": "private",
                    "processing_time_ms": 1250.5
                },
                {
                    "response": "Hello everyone! How can I help the group today?",
                    "timestamp": "2024-09-06T17:00:00Z", 
                    "user_id": "clm7x8y9z0000abc123def456",
                    "group_id": "clm7x8y9z0000grp123def789",
                    "conversation_type": "group",
                    "processing_time_ms": 890.2
                }
            ]
        }
    }

class UserCreateRequest(BaseModel):
    """
    Request model for creating or identifying users across platforms.
    
    This model handles user unification across different client platforms.
    """
    whatsapp_id: Optional[str] = Field(None, description="WhatsApp user identifier")
    telegram_id: Optional[str] = Field(None, description="Telegram user identifier") 
    api_id: Optional[str] = Field(None, description="API client user identifier")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "whatsapp_id": "1234567890@c.us",
                "telegram_id": "123456789",
                "api_id": None
            }
        }
    }

class UserResponse(BaseModel):
    """
    Response model for user operations.
    
    This model represents user information returned by the service.
    """
    id: str = Field(..., description="Unique user identifier (CUID)")
    whatsapp_id: Optional[str] = Field(None, description="WhatsApp user identifier")
    telegram_id: Optional[str] = Field(None, description="Telegram user identifier")
    api_id: Optional[str] = Field(None, description="API client user identifier")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="User last update timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "clm7x8y9z0000abc123def456",
                "whatsapp_id": "1234567890@c.us",
                "telegram_id": "123456789",
                "api_id": None,
                "created_at": "2024-09-06T16:00:00Z",
                "updated_at": "2024-09-06T16:00:00Z"
            }
        }
    }

class ConversationHistoryRequest(BaseModel):
    """
    Request model for retrieving conversation history.
    """
    user_id: str = Field(..., description="User identifier to get history for")
    limit: Optional[int] = Field(50, ge=1, le=500, description="Maximum number of messages to retrieve")
    offset: Optional[int] = Field(0, ge=0, description="Number of messages to skip for pagination")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "clm7x8y9z0000abc123def456",
                "limit": 50,
                "offset": 0
            }
        }
    }

class ConversationMessage(BaseModel):
    """
    Model representing a single conversation message.
    """
    id: str = Field(..., description="Message identifier")
    message: str = Field(..., description="Message content")
    sender: MessageSender = Field(..., description="Message sender (USER or AI)")
    timestamp: datetime = Field(..., description="Message timestamp")
    context: Optional[str] = Field(None, description="Message context")

class ConversationHistoryResponse(BaseModel):
    """
    Response model for conversation history requests.
    """
    user_id: str = Field(..., description="User identifier")
    messages: list[ConversationMessage] = Field(..., description="List of conversation messages")
    total_count: int = Field(..., description="Total number of messages for this user")
    has_more: bool = Field(..., description="Whether there are more messages available")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "clm7x8y9z0000abc123def456",
                "messages": [
                    {
                        "id": "msg_001",
                        "message": "Hello!",
                        "sender": "USER",
                        "timestamp": "2024-09-06T16:30:00Z",
                        "context": None
                    },
                    {
                        "id": "msg_002", 
                        "message": "Hello! How can I help you today?",
                        "sender": "AI",
                        "timestamp": "2024-09-06T16:30:01Z",
                        "context": None
                    }
                ],
                "total_count": 2,
                "has_more": False
            }
        }
    }

class ErrorResponse(BaseModel):
    """
    Standard error response model.
    """
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Error timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "Invalid request",
                "detail": "The message field cannot be empty",
                "timestamp": "2024-09-06T17:00:00Z"
            }
        }
    }

class HealthResponse(BaseModel):
    """
    Health check response model.
    """
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Health check timestamp")
    ai_service_healthy: Optional[bool] = Field(None, description="AI service health status")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "service": "ai-core",
                "timestamp": "2024-09-06T17:00:00Z",
                "ai_service_healthy": True
            }
        }
    }