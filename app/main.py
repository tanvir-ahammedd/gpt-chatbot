"""
FastAPI application entry point.

Initializes the FastAPI framework, configures middleware (CORS),
includes API routers, and handles startup/shutdown events.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings, init_db, limiter
from app.routes.chat import router as chat_router

settings = get_settings()

def create_app() -> FastAPI:
    """
    Application factory pattern to create and configure the FastAPI app.
    
    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="A ChatGPT-style conversational AI chatbot with persistent memory.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Attach limiter to app state (required by slowapi)
    app.state.limiter = limiter

    # Register the 429 Too Many Requests exception handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Configure CORS
    app.add_middleware(CORSMiddleware,
        allow_origins=["*"],  # Adjust in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add slowapi middleware for rate limiting
    app.add_middleware(SlowAPIMiddleware)

    # Include API routers
    app.include_router(chat_router)

    # Note: using @app.on_event("startup") is deprecated in newer FastAPI versions
    # but still widely used. Using lifespan is modern, but keeping it simple.
    @app.on_event("startup")
    def startup_event():
        """
        Execute tasks on application startup.
        Initializes the database schema if it doesn't already exist.
        """
        init_db()

    return app

# The main application instance to be run by Uvicorn
app = create_app()

