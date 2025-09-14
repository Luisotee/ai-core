# AI Chatbot Foundation - Claude Development Guide

## Project Overview

This is the **AI Core Service** for a multi-client AI chatbot foundation system. The project provides a centralized AI service that can handle conversations from multiple platforms (WhatsApp, Telegram, API) while maintaining strict conversation context separation between groups and private chats.

### Key Principles

1. **Context Separation is Critical**: Group and private conversations must NEVER mix
2. **Async-First Architecture**: All database operations use SQLAlchemy async patterns
3. **Multi-Platform Support**: Users can be identified across WhatsApp, Telegram, and API
4. **Clean Architecture**: Separation between models, services, and API endpoints
5. **Type Safety**: Extensive use of Pydantic models and SQLAlchemy typing

## Repository Structure

```
ai-core/
├── src/
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── base.py            # Database configuration and Base
│   │   ├── user.py            # User model with platform IDs
│   │   ├── group.py           # Group and GroupMember models
│   │   ├── conversation.py    # Conversation model with context separation
│   │   └── __init__.py        # Model exports
│   ├── services/
│   │   └── database_service.py # Async database operations
│   ├── agents/
│   │   └── manager_agent.py   # smolagents AI integration
│   ├── ai_service.py          # Main AI service coordinator
│   ├── pydantic_models.py     # API request/response models
│   └── __init__.py            # Package exports
├── alembic/                   # Database migrations
├── data/                      # SQLite database storage
├── main.py                    # FastAPI application
├── pyproject.toml            # Poetry dependencies
└── CLAUDE.md                 # This file
```

## Development Methodology

### Database Operations
- **Always use async**: All database operations must be async using SQLAlchemy
- **Context separation**: `group_id=None` for private, `group_id=value` for group conversations
- **Type safety**: Use proper SQLAlchemy `Mapped[T]` and `mapped_column()` syntax
- **Session management**: Use `AsyncSessionLocal()` context managers

### API Development
- **FastAPI async endpoints**: All endpoints should be async with proper dependency injection
- **Pydantic validation**: Comprehensive request/response models with examples
- **Error handling**: Proper HTTP status codes (400, 404, 500) with ErrorResponse models
- **Pagination**: Support limit/offset with has_more and total_count

### Code Quality Standards
- **No unnecessary abstractions**: Keep implementations simple and obvious
- **Explicit over implicit**: Be explicit about types, parameters, and behavior
- **Remove dead code early**: Don't let unused code accumulate
- **Consistent patterns**: Follow established patterns throughout the codebase

## Current Architecture Status

### ✅ Completed Components
- **Database Layer**: SQLAlchemy models with async support
- **User Management**: Multi-platform user identification and unification
- **Group Support**: Groups, membership, and role management
- **Conversation System**: Context-separated conversation storage and retrieval
- **AI Integration**: smolagents-based AI service with context awareness
- **REST API**: Chat endpoint and history endpoints with group support

### 🚧 In Progress
- **Task 5.0**: Building REST API for Client Communication
  - ✅ 5.1 POST /api/v1/chat (with group support)
  - ✅ 5.2 GET /api/v1/users/{user_id}/history
  - ✅ 5.3 GET /api/v1/groups/{group_id}/history
  - ⏳ Next: 5.4 POST /api/v1/users endpoint

## Critical Implementation Details

### Context Separation (MUST MAINTAIN)
```python
# Private conversations: group_id=None
private_history = await db_service.get_conversation_history(
    user_id=user_id,
    group_id=None  # Critical: ensures private conversations only
)

# Group conversations: group_id=specific_group
group_history = await db_service.get_conversation_history(
    user_id=user_id,
    group_id=group_id  # Critical: ensures group conversations only
)
```

### User Identification Patterns
```python
# Users can be identified by any platform
user = await db_service.find_or_create_user(
    whatsapp_id="1234567890@c.us",    # Optional
    telegram_id="987654321",          # Optional  
    api_id="api_user_123"             # Optional
)
# At least one platform ID must be provided
```

### Database Migration Commands
```bash
# Create new migration after model changes
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# View current migration status
poetry run alembic current
```

### Testing Patterns
```bash
# Run API tests
poetry run python -c "from fastapi.testclient import TestClient; ..."

# Start development server
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Health check
curl http://localhost:8000/health
```

## Common Development Tasks

### Adding New API Endpoints
1. Create Pydantic request/response models in `src/pydantic_models.py`
2. Add database methods to `src/services/database_service.py` if needed
3. Implement endpoint in `main.py` with proper async patterns
4. Add error handling and validation
5. Test with both success and error cases

### Database Schema Changes
1. Modify SQLAlchemy models in `src/models/`
2. Generate migration: `poetry run alembic revision --autogenerate -m "description"`
3. Review generated migration file
4. Apply migration: `poetry run alembic upgrade head`
5. Update related service methods if needed

### AI Service Integration
- AI context is automatically generated from conversation history
- Context maintains group/private separation
- Use `ai_service.process_query(query, context)` for AI responses
- Always store both user and AI messages in conversation history

## Dependencies and Tools

### Core Dependencies
- **FastAPI**: Async web framework
- **SQLAlchemy**: Async ORM with SQLite/aiosqlite
- **Alembic**: Database migrations
- **Pydantic**: Data validation and serialization
- **smolagents**: AI agent framework
- **Poetry**: Dependency management

### Development Tools
- **DB Browser for SQLite**: Database visualization (recommended)
- **DBeaver**: Alternative database client
- **SQLite command line**: Quick database inspection

## Environment Variables

```bash
# Required
OPENAI_API_KEY=your_openai_api_key

# Optional (with defaults)
AI_CORE_HOST=localhost          # Default: localhost
AI_CORE_PORT=8000              # Default: 8000
AI_MAX_STEPS=5                 # Default: 5
DATABASE_URL=sqlite:///data/dev.db  # Default path
```

## Database Design and User Unification System

### Core Database Schema

The system uses SQLite with SQLAlchemy ORM and follows a normalized design that supports multi-platform user identification and strict conversation context separation.

#### Database Tables Overview

```sql
-- Users: Multi-platform user identification
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,           -- CUID
    whatsapp_id VARCHAR(50) UNIQUE,       -- WhatsApp: digits@c.us
    telegram_id VARCHAR(20) UNIQUE,       -- Telegram: numeric
    api_id VARCHAR(100) UNIQUE,           -- API: any string
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Groups: WhatsApp/Telegram group management
CREATE TABLE groups (
    id VARCHAR(36) PRIMARY KEY,           -- CUID
    name VARCHAR(200),                    -- Group display name
    description TEXT,                     -- Optional description
    whatsapp_id VARCHAR(50) UNIQUE,       -- WhatsApp: digits@g.us
    telegram_id VARCHAR(20) UNIQUE,       -- Telegram: negative numeric
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Group Membership: User-Group relationships
CREATE TABLE group_members (
    id VARCHAR(36) PRIMARY KEY,           -- CUID
    user_id VARCHAR(36) REFERENCES users(id),
    group_id VARCHAR(36) REFERENCES groups(id),
    role VARCHAR(20) DEFAULT 'MEMBER',    -- MEMBER, ADMIN, OWNER
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    left_at DATETIME NULL                 -- NULL = still member
);

-- Conversations: Message storage with context separation
CREATE TABLE conversations (
    id VARCHAR(36) PRIMARY KEY,           -- CUID
    user_id VARCHAR(36) REFERENCES users(id),
    group_id VARCHAR(36) REFERENCES groups(id) NULL, -- NULL = private
    message TEXT NOT NULL,
    sender VARCHAR(10) NOT NULL,          -- USER, AI
    platform VARCHAR(20),                 -- WHATSAPP, TELEGRAM, API
    message_type VARCHAR(20) DEFAULT 'TEXT',
    context TEXT,                         -- Optional context
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### Critical Indexes for Performance

```sql
-- Context separation indexes
CREATE INDEX idx_conversations_user_private ON conversations(user_id, group_id) WHERE group_id IS NULL;
CREATE INDEX idx_conversations_group ON conversations(group_id) WHERE group_id IS NOT NULL;
CREATE INDEX idx_conversations_timestamp ON conversations(timestamp DESC);

-- User lookup indexes
CREATE INDEX idx_users_whatsapp ON users(whatsapp_id);
CREATE INDEX idx_users_telegram ON users(telegram_id);
CREATE INDEX idx_users_api ON users(api_id);

-- Group lookup indexes
CREATE INDEX idx_groups_whatsapp ON groups(whatsapp_id);
CREATE INDEX idx_groups_telegram ON groups(telegram_id);
CREATE INDEX idx_group_members_active ON group_members(user_id, group_id) WHERE left_at IS NULL;
```

### User Unification System

The user unification system allows users to be identified across multiple platforms while maintaining a single user identity in the database.

#### How User Unification Works

1. **Platform ID Validation**: Each platform has specific ID format requirements
2. **User Lookup**: Search for existing users by any provided platform ID
3. **User Creation**: If no user found, create new user with provided platform IDs
4. **ID Linking**: Future requests can link additional platform IDs to existing users

#### Platform ID Formats

```python
# WhatsApp User IDs
WHATSAPP_USER_PATTERN = r'^\d+@c\.us$'
# Examples: "1234567890@c.us", "5551234567@c.us"

# WhatsApp Group IDs  
WHATSAPP_GROUP_PATTERN = r'^\d+@g\.us$'
# Examples: "120363025343298878@g.us"

# Telegram User IDs
TELEGRAM_USER_PATTERN = r'^\d+$'
# Examples: "123456789", "987654321"

# Telegram Group IDs
TELEGRAM_GROUP_PATTERN = r'^-\d+$'
# Examples: "-123456789", "-987654321"

# API User IDs
API_USER_PATTERN = r'^.+$'  # Any non-empty string
# Examples: "user_123", "api_client_abc", "custom_id_xyz"
```

#### User Lookup Algorithm

```python
async def find_or_create_user(
    whatsapp_id: Optional[str] = None,
    telegram_id: Optional[str] = None,
    api_id: Optional[str] = None
) -> User:
    """
    Find existing user or create new one with platform unification.
    
    Search order:
    1. WhatsApp ID (if provided)
    2. Telegram ID (if provided)  
    3. API ID (if provided)
    
    If user found: return existing user
    If no user found: create new user with all provided IDs
    """
    
    # Try to find existing user by any platform ID
    user = None
    if whatsapp_id:
        user = await get_user_by_platform_id("whatsapp", whatsapp_id)
    if not user and telegram_id:
        user = await get_user_by_platform_id("telegram", telegram_id)
    if not user and api_id:
        user = await get_user_by_platform_id("api", api_id)
    
    if user:
        return user
    
    # Create new user with all provided platform IDs
    return await create_user(
        whatsapp_id=whatsapp_id,
        telegram_id=telegram_id,
        api_id=api_id
    )
```

#### User Unification Examples

**Example 1: New User Registration**
```python
# First contact via WhatsApp
user = await find_or_create_user(whatsapp_id="1234567890@c.us")
# Creates: User(id="abc123", whatsapp_id="1234567890@c.us", telegram_id=None, api_id=None)

# Later contact via Telegram (would need manual linking in advanced implementation)
# Currently creates separate user - future enhancement could link them
```

**Example 2: Multi-Platform User Creation**
```python
# User provides multiple platform IDs in single request
user = await find_or_create_user(
    whatsapp_id="1234567890@c.us",
    telegram_id="987654321",
    api_id="user_alpha"
)
# Creates: User with all three platform IDs linked
```

**Example 3: Existing User Lookup**
```python
# User already exists with WhatsApp ID
existing_user = await find_or_create_user(whatsapp_id="1234567890@c.us")
# Returns: Existing user, no new user created
```

### Context Separation Architecture

Context separation is the **most critical feature** ensuring group and private conversations never mix.

#### How Context Separation Works

```python
# Private conversations: group_id = NULL
private_conversations = await get_conversation_history(
    user_id="abc123",
    group_id=None  # Explicit NULL for private conversations
)

# Group conversations: group_id = specific group
group_conversations = await get_conversation_history(
    user_id="abc123", 
    group_id="group_xyz"  # Specific group only
)

# Result: Private and group conversations are completely separate
```

#### Database Queries for Context Separation

```sql
-- Get private conversations (group_id IS NULL)
SELECT * FROM conversations 
WHERE user_id = ? AND group_id IS NULL 
ORDER BY timestamp DESC;

-- Get group conversations (group_id = specific value)
SELECT * FROM conversations 
WHERE user_id = ? AND group_id = ? 
ORDER BY timestamp DESC;

-- Get all group conversations (any group_id)
SELECT * FROM conversations 
WHERE group_id = ? 
ORDER BY timestamp DESC;
```

#### AI Context Generation with Separation

```python
async def get_conversation_context_for_ai(
    user_id: str,
    group_id: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    Generate AI context maintaining strict separation.
    
    CRITICAL: group_id parameter ensures contexts never mix!
    """
    conversations = await get_conversation_history(
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
    return f"Recent {context_type} conversation:\\n" + "\\n".join(context_lines)
```

### Group Management System

#### Group Creation and Membership

```python
# Group creation workflow
async def handle_group_message(request: ChatRequest):
    """Handle group message with automatic group creation."""
    
    # 1. Find or create user
    user = await find_or_create_user(
        whatsapp_id=request.whatsapp_id,
        telegram_id=request.telegram_id,
        api_id=request.api_id
    )
    
    # 2. Find or create group
    group = await find_or_create_group(
        name=request.group_name,
        whatsapp_id=request.group_whatsapp_id,
        telegram_id=request.group_telegram_id
    )
    
    # 3. Ensure user is group member
    membership = await get_group_membership(user.id, group.id)
    if not membership:
        await add_user_to_group(user.id, group.id, role=GroupRole.MEMBER)
    
    # 4. Store message with group context
    await add_conversation(
        user_id=user.id,
        group_id=group.id,  # Group context
        message=request.message,
        sender=MessageSender.USER
    )
```

#### Group Roles and Permissions

```python
class GroupRole(str, Enum):
    MEMBER = "MEMBER"    # Regular member
    ADMIN = "ADMIN"      # Group administrator  
    OWNER = "OWNER"      # Group owner

# Group membership tracking
class GroupMember:
    user_id: str
    group_id: str
    role: GroupRole
    joined_at: datetime
    left_at: Optional[datetime] = None  # NULL = still member
```

### Database Migration Strategy

#### Alembic Migration Management

```bash
# Create new migration after model changes
poetry run alembic revision --autogenerate -m "Add new feature"

# Review generated migration before applying
# Edit migration file if needed for custom logic

# Apply migration
poetry run alembic upgrade head

# Check current migration status
poetry run alembic current

# Rollback if needed (use with caution)
poetry run alembic downgrade -1
```

#### Migration Best Practices

1. **Always review auto-generated migrations** before applying
2. **Add custom data migrations** when changing data structure
3. **Test migrations on copy of production data**
4. **Use descriptive migration messages**
5. **Never edit applied migrations** - create new ones instead

#### Example Migration Scenarios

**Adding New Column**
```python
def upgrade():
    op.add_column('users', sa.Column('phone_number', sa.String(20), nullable=True))

def downgrade():
    op.drop_column('users', 'phone_number')
```

**Data Migration**
```python
def upgrade():
    # Add new column
    op.add_column('conversations', sa.Column('message_type', sa.String(20), nullable=True))
    
    # Update existing data
    connection = op.get_bind()
    connection.execute(
        "UPDATE conversations SET message_type = 'TEXT' WHERE message_type IS NULL"
    )
    
    # Make column non-nullable
    op.alter_column('conversations', 'message_type', nullable=False)
```

### Performance Considerations

#### Query Optimization

```python
# Good: Use specific indexes for context separation
query = select(Conversation).where(
    and_(
        Conversation.user_id == user_id,
        Conversation.group_id == group_id  # Uses compound index
    )
).order_by(desc(Conversation.timestamp)).limit(limit)

# Good: Use selectinload for related data
query = select(User).options(
    selectinload(User.group_memberships)
).where(User.id == user_id)

# Avoid: N+1 queries
# Instead of loading conversations in loop, use batch loading
```

#### Connection Management

```python
# Good: Use async context managers
async with AsyncSessionLocal() as session:
    # Perform multiple operations
    user = await session.get(User, user_id)
    conversations = await session.execute(query)
    await session.commit()

# Good: Use dependency injection for FastAPI
async def endpoint(db_service: DatabaseService = Depends(get_database_service)):
    return await db_service.some_operation()
```

## Communication Guidelines

### Error Reporting
- Always include full error messages and stack traces
- Specify which endpoint or operation failed
- Include request/response examples when relevant
- Test both success and failure cases

### Code Reviews
- Verify context separation is maintained
- Check for proper async patterns
- Ensure type safety with Pydantic/SQLAlchemy
- Validate error handling covers edge cases
- Confirm database operations use proper session management

### Pull Request Guidelines
- **Size**: Aim for ~500 lines, max 1000 lines
- **Scope**: Complete one meaningful unit of work
- **Testing**: Include test examples or verification steps
- **Documentation**: Update CLAUDE.md if architecture changes

## Quick Reference Commands

```bash
# Development server
poetry run uvicorn main:app --reload

# Database migrations
poetry run alembic upgrade head
poetry run alembic revision --autogenerate -m "description"

# Database inspection
sqlite3 data/dev.db ".tables"
sqlite3 data/dev.db "SELECT * FROM conversations LIMIT 5;"

# API testing
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","whatsapp_id":"123@c.us","platform":"WHATSAPP"}'

# Health check
curl http://localhost:8000/health
```

## Current Task Context

**Working on Task 5.0**: Build REST API for Client Communication

**Next Task**: 5.4 Create POST /api/v1/users endpoint for user registration/identification

**Progress**: 3/7 endpoints completed (5.1, 5.2, 5.3 done)

When implementing new endpoints, always follow the established patterns for async operations, error handling, and maintain the critical context separation between group and private conversations.

---

**Last Updated**: 2025-09-14  
**Project Status**: Active Development  
**Current Version**: 0.1.0