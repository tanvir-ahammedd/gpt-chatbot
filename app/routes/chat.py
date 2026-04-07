"""
Chat API route handlers.

Defines all HTTP endpoints for the chatbot: sending messages,
retrieving history, deleting sessions, and health checks.
Rate limiting is applied per client IP using slowapi.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import get_settings, get_db, limiter
from app.models.schemas import (
    ChatRequest, ChatResponse, HistoryResponse, MessageEntry,
    DeleteResponse, HealthResponse, ErrorResponse
)
from app.services.ai import ai_service
from app.services.memory import memory_service
from app.config import get_settings

settings = get_settings()
router = APIRouter(tags=["Chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        429: {"model": ErrorResponse, "description": "Rate Limit Exceeded"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_RPM}/minute")
def chat_endpoint(request: Request, body: ChatRequest, db: Session = Depends(get_db)):
    """
    Send a message and receive an AI response.

    Rate-limited to RATE_LIMIT_RPM requests per minute per IP.
    Saves both the user message and AI reply to the PostgreSQL memory store.
    """
    try:
        # 1. Save user message to memory
        memory_service.add_message(
            db=db,
            session_id=body.session_id,
            role="user",
            content=body.message
        )

        # 2. Retrieve session context for AI
        context = memory_service.get_context(db, body.session_id)

        # 3. Generate AI response
        ai_response_text = ai_service.generate_response(
            user_message=body.message,
            conversation_history=context
        )

        # 4. Save AI message to memory
        memory_service.add_message(
            db=db,
            session_id=body.session_id,
            role="assistant",
            content=ai_response_text
        )

        # 5. Return response
        return ChatResponse(
            session_id=body.session_id,
            response=ai_response_text
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the chat: {str(e)}"
        )


@router.get(
    "/history/{session_id}",
    response_model=HistoryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session Not Found"},
        429: {"model": ErrorResponse, "description": "Rate Limit Exceeded"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    }
)
@limiter.limit("60/minute")
def get_history(request: Request, session_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the full conversation history for a given session.

    Rate-limited to 60 requests per minute per IP.
    """
    if not memory_service.session_exists(db, session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found."
        )

    messages = memory_service.get_history(db, session_id)
    message_entries = [
        MessageEntry(
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp
        )
        for msg in messages
    ]

    return HistoryResponse(
        session_id=session_id,
        messages=message_entries,
        message_count=len(message_entries)
    )


@router.delete(
    "/history/{session_id}",
    response_model=DeleteResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session Not Found"},
        429: {"model": ErrorResponse, "description": "Rate Limit Exceeded"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    }
)
@limiter.limit("30/minute")
def delete_history(request: Request, session_id: str, db: Session = Depends(get_db)):
    """
    Clear / reset the conversation memory for a session.

    Rate-limited to 30 requests per minute per IP.
    """
    if not memory_service.session_exists(db, session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found."
        )

    success = memory_service.clear_history(db, session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear memory."
        )

    return DeleteResponse(
        session_id=session_id,
        message="Session history cleared successfully."
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        429: {"model": ErrorResponse, "description": "Rate Limit Exceeded"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    }
)
@limiter.limit("60/minute")
def health_check(request: Request, db: Session = Depends(get_db)):
    """
    Health-check endpoint returning service status.

    Rate-limited to 60 requests per minute per IP.
    """
    try:
        active_sessions = memory_service.get_active_session_count(db)
        # Check AI service health
        ai_healthy = ai_service.health_check()

        return HealthResponse(
            status="healthy" if ai_healthy else "degraded",
            version=settings.APP_VERSION,
            active_sessions=active_sessions,
            model=settings.MODEL_NAME
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.post(
    "/chat/stream",
    response_class=StreamingResponse,
    responses={
        429: {"model": ErrorResponse, "description": "Rate Limit Exceeded"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Streaming Chat (SSE)",
    description=(
        "Send a message and receive the AI response as a real-time stream "
        "of Server-Sent Events (SSE). Each event contains a JSON payload "
        "with a `content` field. The final event has `done: true`."
    ),
)
@limiter.limit(f"{settings.RATE_LIMIT_RPM}/minute")
def chat_stream(request: Request, body: ChatRequest, db: Session = Depends(get_db)):
    """
    Stream an AI response token by token using Server-Sent Events.

    SSE event format:
        data: {"content": "<token>"}
        data: {"content": "", "done": true, "session_id": "<id>"}
    """
    try:
        memory_service.add_message(db=db, session_id=body.session_id, role="user", content=body.message)
        context = memory_service.get_context(db, body.session_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to initialise stream: {str(e)}")

    def event_generator():
        collected_chunks: list[str] = []
        for chunk in ai_service.generate_response_stream(user_message=body.message, conversation_history=context):
            collected_chunks.append(chunk)
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        complete_response = "".join(collected_chunks)
        if complete_response:
            memory_service.add_message(db=db, session_id=body.session_id, role="assistant", content=complete_response)
        yield f"data: {json.dumps({'content': '', 'done': True, 'session_id': body.session_id})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
