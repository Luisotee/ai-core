"""
AI Core Service - Main FastAPI Application

This module provides the main FastAPI application for the AI chatbot core service.
It handles HTTP requests and integrates with the smolagents AI system.
"""

from fastapi import FastAPI, HTTPException, Depends, Request, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
import os
import time
import logging
from datetime import datetime, timezone
from src import get_ai_service
from src.pydantic_models import ChatRequest, ChatResponse, ErrorResponse, ConversationHistoryResponse, ConversationMessage
from pydantic import Field
from fastapi import Path, Query
from src.services.database_service import get_database_service, DatabaseService
from src.models import MessageSender, Platform as DBPlatform

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get configuration from environment variables
AI_CORE_HOST = os.getenv("AI_CORE_HOST", "localhost")
AI_CORE_PORT = int(os.getenv("AI_CORE_PORT", 8000))

# Initialize FastAPI application
app = FastAPI(
    title="AI Chatbot Foundation - Core Service",
    description="""
    ## Multi-Platform AI Chatbot Core Service
    
    A centralized AI service that handles conversations from multiple platforms (WhatsApp, Telegram, API) 
    while maintaining strict conversation context separation between groups and private chats.
    
    ### Key Features
    
    * **Multi-Platform Support**: WhatsApp, Telegram, and direct API access
    * **Context Separation**: Private and group conversations are completely isolated
    * **User Unification**: Automatic user identification across platforms
    * **Group Management**: Automatic group creation and membership tracking
    * **AI Integration**: Powered by smolagents for intelligent responses
    
    ### Platform ID Formats
    
    * **WhatsApp User**: `1234567890@c.us`
    * **WhatsApp Group**: `120363025343298878@g.us`  
    * **Telegram User**: `123456789` (numeric)
    * **Telegram Group**: `-123456789` (negative numeric)
    * **API User**: Any string identifier
    
    ### Authentication
    
    Currently no authentication required. In production, implement proper authentication.
    
    ### Rate Limiting
    
    No rate limiting currently implemented. Consider adding rate limits for production use.
    """,
    version="0.1.0",
    contact={
        "name": "AI Chatbot Foundation",
        "url": "https://github.com/your-org/chat-bot",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": f"http://{AI_CORE_HOST}:{AI_CORE_PORT}",
            "description": "Development server"
        }
    ]
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with detailed error messages"""
    logger.warning(f"Validation error on {request.method} {request.url}: {exc}")
    
    error_details = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append(f"{field}: {error['msg']}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation Error",
            detail="Request validation failed: " + "; ".join(error_details),
            timestamp=datetime.now(timezone.utc)
        ).model_dump()
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors with 400 status"""
    logger.warning(f"Value error on {request.method} {request.url}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="Invalid Request",
            detail=str(exc),
            timestamp=datetime.now(timezone.utc)
        ).model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors with 500 status"""
    logger.error(f"Unexpected error on {request.method} {request.url}: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error",
            detail="An unexpected error occurred while processing your request",
            timestamp=datetime.now(timezone.utc)
        ).model_dump()
    )

@app.get(
    "/",
    tags=["System"],
    summary="Service Information",
    description="Get basic information about the AI Core Service including version and status."
)
async def root():
    """Root endpoint returning service information"""
    return {
        "service": "AI Core Service",
        "version": "0.1.0",
        "status": "running"
    }

@app.get(
    "/health",
    tags=["System"],
    summary="Health Check",
    description="Check the health status of the AI Core Service including database connectivity and AI service status.",
    response_description="Health status information including service status, database connectivity, and timestamps."
)
async def health_check():
    """Health check endpoint for service monitoring"""
    try:
        # Get AI service instance and perform health check
        ai_service = get_ai_service()
        health_result = await ai_service.health_check()
        
        # Add timestamp to the response
        health_result["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return health_result
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "ai-core",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.post(
    "/api/v1/chat", 
    response_model=ChatResponse, 
    status_code=status.HTTP_200_OK,
    tags=["Chat"],
    summary="Send Chat Message",
    description="""
    Send a message to the AI service for processing. Supports both private and group conversations.
    
    ## Message Types
    
    ### Private Message
    Send a private message by providing user platform ID only (no group IDs).
    
    ### Group Message  
    Send a group message by providing both user platform ID and group platform ID.
    
    ## User Identification
    
    At least one platform ID must be provided:
    - `whatsapp_id`: WhatsApp user ID in format `digits@c.us`
    - `telegram_id`: Telegram user ID (numeric string)
    - `api_id`: Custom API user identifier (any string)
    
    ## Group Identification (Optional)
    
    For group messages, provide group platform ID:
    - `group_whatsapp_id`: WhatsApp group ID in format `digits@g.us`
    - `group_telegram_id`: Telegram group ID (negative numeric string)
    - `group_name`: Human-readable group name
    
    ## Context Separation
    
    The system maintains strict separation between private and group conversations.
    Private conversations will never appear in group history and vice versa.
    """,
    response_description="AI response with conversation metadata and processing information",
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request - Invalid input parameters (e.g., no platform ID provided)"},
        422: {"model": ErrorResponse, "description": "Unprocessable Entity - Validation error (e.g., invalid platform ID format)"},
        500: {"model": ErrorResponse, "description": "Internal Server Error - Unexpected server error"}
    }
)
async def chat_endpoint(
    request: ChatRequest,
    response: Response,
    db_service: DatabaseService = Depends(get_database_service)
):
    """
    Chat endpoint for sending messages with group support.
    
    This endpoint handles both private messages and group messages, maintaining
    strict conversation context separation between groups and private chats.
    """
    start_time = time.time()
    
    try:
        # Validate that at least one platform ID is provided
        if not any([request.whatsapp_id, request.telegram_id, request.api_id]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one platform ID (whatsapp_id, telegram_id, or api_id) must be provided"
            )
        
        # Find or create user
        user = await db_service.find_or_create_user(
            whatsapp_id=request.whatsapp_id,
            telegram_id=request.telegram_id,
            api_id=request.api_id
        )
        
        # Determine if this is a group message and handle group creation
        group_id = None
        conversation_type = "private"
        
        if request.group_whatsapp_id or request.group_telegram_id:
            conversation_type = "group"
            
            # Find or create group
            group = await db_service.find_or_create_group(
                name=request.group_name,
                whatsapp_id=request.group_whatsapp_id,
                telegram_id=request.group_telegram_id
            )
            group_id = group.id
            
            # Ensure user is a member of the group
            existing_membership = await db_service.get_group_membership(user.id, group.id)
            if not existing_membership:
                await db_service.add_user_to_group(user.id, group.id)
        
        # Convert platform enum
        db_platform = None
        if request.platform:
            db_platform = DBPlatform(request.platform.value)
        
        # Store user message in conversation history
        await db_service.add_conversation(
            user_id=user.id,
            group_id=group_id,
            message=request.message,
            sender=MessageSender.USER,
            platform=db_platform,
            context=request.context
        )
        
        # Get conversation context for AI (maintains group/private separation)
        ai_context = await db_service.get_conversation_context_for_ai(
            user_id=user.id,
            group_id=group_id,
            limit=10
        )
        
        # Get AI service and process the message
        ai_service = get_ai_service()
        ai_response = ai_service.process_query(
            query=request.message,
            context={
                "user_id": user.id,
                "group_id": group_id,
                "conversation_context": ai_context,
                "conversation_type": conversation_type
            }
        )
        
        # Store AI response in conversation history
        await db_service.add_conversation(
            user_id=user.id,
            group_id=group_id,
            message=ai_response,
            sender=MessageSender.AI,
            platform=db_platform
        )
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Add response headers
        response.headers["X-Processing-Time"] = f"{processing_time_ms:.2f}ms"
        response.headers["X-Conversation-Type"] = conversation_type
        response.headers["X-AI-Core-Version"] = "0.1.0"
        
        return ChatResponse(
            response=ai_response,
            user_id=user.id,
            group_id=group_id,
            conversation_type=conversation_type,
            processing_time_ms=processing_time_ms
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except ValueError as e:
        # Handle value errors (will be caught by global handler)
        logger.warning(f"Value error in chat endpoint: {e}")
        raise
    except Exception as e:
        # Log unexpected errors for debugging
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        raise

@app.get(
    "/api/v1/users/{user_id}/history", 
    response_model=ConversationHistoryResponse,
    status_code=status.HTTP_200_OK,
    tags=["History"],
    summary="Get User Conversation History",
    description="""
    Retrieve private conversation history for a specific user.
    
    ## Context Separation
    
    This endpoint returns **ONLY private conversations** between the user and the AI.
    Group conversations are completely separate and handled by the group history endpoint.
    
    ## Pagination
    
    Use `limit` and `offset` parameters for pagination:
    - `limit`: Number of messages to retrieve (1-500, default: 50)
    - `offset`: Number of messages to skip (≥0, default: 0)
    
    ## Response Headers
    
    The response includes helpful headers:
    - `X-Total-Count`: Total number of messages available
    - `X-Has-More`: Whether more messages are available
    - `X-Conversation-Type`: Always "private" for this endpoint
    
    ## Message Ordering
    
    Messages are returned in chronological order (oldest first) within the requested page.
    """,
    response_description="Paginated list of private conversation messages with metadata",
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request - Invalid parameters (limit out of range, negative offset)"},
        404: {"model": ErrorResponse, "description": "Not Found - User with specified ID does not exist"},
        422: {"model": ErrorResponse, "description": "Unprocessable Entity - Validation error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error - Database or system error"}
    }
)
async def get_user_conversation_history(
    user_id: str = Path(..., description="Unique user identifier (CUID)", examples=["clm7x8y9z0000abc123def456"]),
    response: Response = None,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of messages to retrieve"),
    offset: int = Query(0, ge=0, description="Number of messages to skip for pagination"),
    db_service: DatabaseService = Depends(get_database_service)
):
    """
    Get conversation history for a specific user (private conversations only).
    
    This endpoint retrieves the private conversation history between the user and the AI.
    Group conversations are handled by a separate endpoint to maintain context separation.
    
    Args:
        user_id: The user's unique identifier
        limit: Maximum number of messages to retrieve (1-500, default: 50)
        offset: Number of messages to skip for pagination (default: 0)
    """
    try:
        # Validate parameters
        if limit < 1 or limit > 500:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 500"
            )
        
        if offset < 0:
            raise HTTPException(
                status_code=400,
                detail="Offset must be non-negative"
            )
        
        # Check if user exists
        user = await db_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id '{user_id}' not found"
            )
        
        # Get private conversation history (group_id=None ensures private conversations only)
        conversations = await db_service.get_conversation_history(
            user_id=user_id,
            group_id=None,  # Private conversations only
            limit=limit + offset  # Get extra to handle offset
        )
        
        # Apply offset and limit
        paginated_conversations = conversations[offset:offset + limit]
        
        # Convert to response format
        messages = []
        for conv in paginated_conversations:
            messages.append(ConversationMessage(
                id=conv.id,
                message=conv.message,
                sender=conv.sender,
                timestamp=conv.timestamp,
                context=conv.context
            ))
        
        # Calculate total count (this is approximate since we're using limit/offset)
        # For exact count, we'd need a separate query, but this is more efficient
        has_more = len(conversations) > offset + limit
        total_count = len(conversations) if not has_more else offset + limit + 1  # Approximate
        
        # Add response headers
        response.headers["X-Total-Count"] = str(total_count)
        response.headers["X-Has-More"] = str(has_more).lower()
        response.headers["X-Conversation-Type"] = "private"
        response.headers["X-AI-Core-Version"] = "0.1.0"
        
        return ConversationHistoryResponse(
            user_id=user_id,
            messages=messages,
            total_count=total_count,
            has_more=has_more
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except ValueError as e:
        # Handle value errors (will be caught by global handler)
        logger.warning(f"Value error in user history endpoint: {e}")
        raise
    except Exception as e:
        # Log unexpected errors for debugging
        logger.error(f"Unexpected error in user history endpoint: {e}", exc_info=True)
        raise

@app.get(
    "/api/v1/groups/{group_id}/history", 
    response_model=ConversationHistoryResponse,
    status_code=status.HTTP_200_OK,
    tags=["History"],
    summary="Get Group Conversation History",
    description="""
    Retrieve conversation history for a specific group.
    
    ## Group Context
    
    This endpoint returns **ALL conversations within the specified group** from all group members.
    Private conversations between individual users and the AI are completely separate.
    
    ## Group Membership
    
    The response includes messages from:
    - All current group members
    - Previous group members (if they sent messages before leaving)
    - AI responses within the group context
    
    ## Pagination
    
    Use `limit` and `offset` parameters for pagination:
    - `limit`: Number of messages to retrieve (1-500, default: 50)
    - `offset`: Number of messages to skip (≥0, default: 0)
    
    ## Response Headers
    
    The response includes helpful headers:
    - `X-Total-Count`: Total number of group messages available
    - `X-Has-More`: Whether more messages are available
    - `X-Conversation-Type`: Always "group" for this endpoint
    
    ## Message Ordering
    
    Messages are returned in chronological order (oldest first) within the requested page.
    """,
    response_description="Paginated list of group conversation messages with metadata",
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request - Invalid parameters (limit out of range, negative offset)"},
        404: {"model": ErrorResponse, "description": "Not Found - Group with specified ID does not exist"},
        422: {"model": ErrorResponse, "description": "Unprocessable Entity - Validation error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error - Database or system error"}
    }
)
async def get_group_conversation_history(
    group_id: str = Path(..., description="Unique group identifier (CUID)", examples=["clm7x8y9z0000grp123def789"]),
    response: Response = None,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of messages to retrieve"),
    offset: int = Query(0, ge=0, description="Number of messages to skip for pagination"),
    db_service: DatabaseService = Depends(get_database_service)
):
    """
    Get conversation history for a specific group.
    
    This endpoint retrieves the group conversation history for all members.
    Only conversations within this specific group are returned to maintain context separation.
    
    Args:
        group_id: The group's unique identifier
        limit: Maximum number of messages to retrieve (1-500, default: 50)
        offset: Number of messages to skip for pagination (default: 0)
    """
    try:
        # Validate parameters
        if limit < 1 or limit > 500:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 500"
            )
        
        if offset < 0:
            raise HTTPException(
                status_code=400,
                detail="Offset must be non-negative"
            )
        
        # Check if group exists
        group = await db_service.get_group_by_id(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group with id '{group_id}' not found"
            )
        
        # Get group conversation history (all conversations in this group)
        conversations = await db_service.get_group_conversation_history(
            group_id=group_id,
            limit=limit + offset  # Get extra to handle offset
        )
        
        # Apply offset and limit
        paginated_conversations = conversations[offset:offset + limit]
        
        # Convert to response format
        messages = []
        for conv in paginated_conversations:
            messages.append(ConversationMessage(
                id=conv.id,
                message=conv.message,
                sender=conv.sender,
                timestamp=conv.timestamp,
                context=conv.context
            ))
        
        # Calculate pagination info
        has_more = len(conversations) > offset + limit
        total_count = len(conversations) if not has_more else offset + limit + 1  # Approximate
        
        # Add response headers
        response.headers["X-Total-Count"] = str(total_count)
        response.headers["X-Has-More"] = str(has_more).lower()
        response.headers["X-Conversation-Type"] = "group"
        response.headers["X-AI-Core-Version"] = "0.1.0"
        
        return ConversationHistoryResponse(
            user_id=f"group:{group_id}",  # Use special format to indicate this is group history
            messages=messages,
            total_count=total_count,
            has_more=has_more
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except ValueError as e:
        # Handle value errors (will be caught by global handler)
        logger.warning(f"Value error in user history endpoint: {e}")
        raise
    except Exception as e:
        # Log unexpected errors for debugging
        logger.error(f"Unexpected error in user history endpoint: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    # Use the already configured environment variables
    logger.info(f"Starting AI Core Service on {AI_CORE_HOST}:{AI_CORE_PORT}")
    logger.info(f"Swagger UI will be available at: http://{AI_CORE_HOST}:{AI_CORE_PORT}/docs")
    logger.info(f"ReDoc will be available at: http://{AI_CORE_HOST}:{AI_CORE_PORT}/redoc")
    
    # Run the application
    uvicorn.run(
        "main:app",
        host=AI_CORE_HOST,
        port=AI_CORE_PORT,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )