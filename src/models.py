"""
Pydantic Models for API Communication

This module defines the request and response models used for API communication
between client applications and the AI core service.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class MessageSender(str, Enum):
    """Enum for message sender types"""
    USER = "USER"
    AI = "AI"

class ChatRequest(BaseModel):
    """
    Request model for chat/query endpoints.
    
    This model represents a user's request to the AI service.
    """
    message: str = Field(..., min_length=1, max_length=10000, description="The user's message or query")
    user_id: Optional[str] = Field(None, description="Optional user identifier for conversation tracking")
    context: Optional[str] = Field(None, max_length=5000, description="Optional conversation context")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "What is the capital of France?",
                "user_id": "user_123",
                "context": "We were discussing European capitals"
            }
        }
    }

class ChatResponse(BaseModel):
    """
    Response model for chat/query endpoints.
    
    This model represents the AI service's response to a user query.
    """
    response: str = Field(..., description="The AI-generated response")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    user_id: Optional[str] = Field(None, description="User identifier if provided in request")
    processing_time_ms: Optional[float] = Field(None, description="Time taken to process the request in milliseconds")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "response": "The capital of France is Paris.",
                "timestamp": "2024-09-06T17:00:00Z",
                "user_id": "user_123",
                "processing_time_ms": 1250.5
            }
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
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
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
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
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