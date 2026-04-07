"""
Pydantic request and response schemas.

Defines all data models used for API request validation
and response serialization.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from app.config import Base


# Request Schemas
class ChatRequest(BaseModel):
    """
    Request body for the POST /chat endpoint.
    
    Attributes:
        session_id: Unique identifier.
        message: The user's message text to send to the AI.
    """
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique session identifier for conversation isolation",
        examples=["session-123", "user-abc-chat-1"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User's message text",
        examples=["Hello, how are you?"],
    )


# Response Schemas
class ChatResponse(BaseModel):
    """
    Response body for the POST /chat endpoint.
    
    Returns the AI-generated reply along with the session identifier.
    """
    session_id: str = Field(
        ...,
        description="Session identifier for this conversation",
    )
    response: str = Field(
        ...,
        description="AI-generated response text",
    )


class MessageEntry(BaseModel):
    """
    Represents a single message in the conversation history.
    
    Each message has a role (user or assistant), content,
    and a timestamp for ordering.
    """
    role: Literal["user", "assistant"] = Field(
        ...,
        description="Who sent this message",
    )
    content: str = Field(
        ...,
        description="The message text content",
    )
    timestamp: datetime = Field(
        ...,
        description="When this message was created (UTC)",
    )


class HistoryResponse(BaseModel):
    """
    Response body for the GET /history/{session_id} endpoint.
    
    Contains the full ordered conversation history for a session.
    """
    session_id: str = Field(
        ...,
        description="Session identifier",
    )
    messages: list[MessageEntry] = Field(
        default_factory=list,
        description="Ordered list of messages in the conversation",
    )
    message_count: int = Field(
        ...,
        description="Total number of messages in this session",
    )


class HealthResponse(BaseModel):
    """
    Response body for the GET /health endpoint.
    
    Provides service health status and basic metrics.
    """
    status: str = Field(
        default="healthy",
        description="Service health status",
    )
    version: str = Field(
        ...,
        description="Application version",
    )
    active_sessions: int = Field(
        ...,
        description="Number of active chat sessions",
    )
    model: str = Field(
        ...,
        description="LLM model currently in use",
    )


class DeleteResponse(BaseModel):
    """
    Response body for the DELETE /history/{session_id} endpoint.
    
    Confirms successful deletion of a session's history.
    """
    session_id: str = Field(
        ...,
        description="Session identifier that was deleted",
    )
    message: str = Field(
        ...,
        description="Confirmation message",
    )


class ErrorResponse(BaseModel):
    """
    Standard error response format.
    
    Used for consistent error messaging across all endpoints.
    """
    detail: str = Field(
        ...,
        description="Human-readable error description",
    )


# Database Models
from datetime import timezone

class ChatMessage(Base):
    """
    Database model for storing individual chat messages.
    
    Each row represents a single message (user or assistant)
    within a specific conversation session.
    
    Table: chat_messages
    Indexes:
        - ix_session_id: For fast session-based queries
        - ix_session_timestamp: For ordered history retrieval
    """
    __tablename__ = "chat_messages"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique message identifier",
    )
    session_id = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Session identifier for conversation isolation",
    )
    role = Column(
        String(20),
        nullable=False,
        comment="Message sender: 'user' or 'assistant'",
    )
    content = Column(
        Text,
        nullable=False,
        comment="Message text content",
    )
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Message creation timestamp (UTC)",
    )

    # Composite index for efficient session history queries
    __table_args__ = (
        Index("ix_session_timestamp", "session_id", "timestamp"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<ChatMessage(id={self.id}, session_id='{self.session_id}', "
            f"role='{self.role}', content='{self.content[:50]}...')>"
        )
