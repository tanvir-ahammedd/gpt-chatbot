"""
Chat memory and session management service.

Handles all operations related to storing, retrieving, and
managing conversation history in PostgreSQL. Each session
is strictly isolated to prevent data leakage between users.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.schemas import ChatMessage
from app.config import get_settings


settings = get_settings()


class ChatMemoryService:
    """
    Service for managing chat conversation memory in PostgreSQL.
    
    Provides methods to store messages, retrieve history,
    clear sessions, and format context for LLM API calls.
    All operations are session-isolated.
    """

    def add_message(
        self, db: Session, session_id: str, role: str, content: str
    ) -> ChatMessage:
        """
        Add a new message to the conversation history.
        
        Args:
            db: SQLAlchemy database session.
            session_id: Unique identifier for the conversation.
            role: Message sender — 'user' or 'assistant'.
            content: The message text content.
            
        Returns:
            The created ChatMessage database record.
        """
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    def get_history(self, db: Session, session_id: str) -> list[ChatMessage]:
        """
        Retrieve the full ordered conversation history for a session.
        
        Args:
            db: SQLAlchemy database session.
            session_id: Unique identifier for the conversation.
            
        Returns:
            List of ChatMessage objects ordered by timestamp (ascending).
        """
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.timestamp.asc())
            .all()
        )

    def clear_history(self, db: Session, session_id: str) -> bool:
        """
        Delete all messages for a given session.
        
        Args:
            db: SQLAlchemy database session.
            session_id: Unique identifier for the conversation.
            
        Returns:
            True if messages were deleted, False if session didn't exist.
        """
        deleted_count = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .delete()
        )
        db.commit()
        return deleted_count > 0

    def session_exists(self, db: Session, session_id: str) -> bool:
        """
        Check if a session has any messages stored.
        
        Args:
            db: SQLAlchemy database session.
            session_id: Unique identifier for the conversation.
            
        Returns:
            True if the session exists, False otherwise.
        """
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .first()
            is not None
        )

    def get_context(self, db: Session, session_id: str) -> list[dict]:
        """
        Format conversation history as a list of dicts for the LLM API.
        
        Applies context truncation if the message count exceeds
        MAX_MESSAGES_PER_SESSION to manage token limits.
        
        Args:
            db: SQLAlchemy database session.
            session_id: Unique identifier for the conversation.
            
        Returns:
            List of dicts with 'role' and 'content' keys,
            suitable for passing to the Groq API.
        """
        messages = self.get_history(db, session_id)

        # Apply context truncation if needed (keep most recent messages)
        max_messages = settings.MAX_MESSAGES_PER_SESSION
        if len(messages) > max_messages:
            messages = messages[-max_messages:]

        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    def get_active_session_count(self, db: Session) -> int:
        """
        Count the number of unique active sessions.
        
        Args:
            db: SQLAlchemy database session.
            
        Returns:
            Number of distinct session IDs in the database.
        """
        result = db.query(
            func.count(func.distinct(ChatMessage.session_id))
        ).scalar()
        return result or 0

    def get_message_count(self, db: Session, session_id: str) -> int:
        """
        Count the number of messages in a specific session.
        
        Args:
            db: SQLAlchemy database session.
            session_id: Unique identifier for the conversation.
            
        Returns:
            Number of messages in the session.
        """
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .count()
        )


# Singleton instance for app-wide use
memory_service = ChatMemoryService()
