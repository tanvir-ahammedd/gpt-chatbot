"""
Application configuration module.

Loads environment variables from .env file and provides
a centralized settings object for the entire application.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All sensitive configuration (API keys, database credentials)
    is managed via .env file — never hardcoded.
    """

    # Groq API Configuration
    GROQ_API_KEY: str = "your-groq-api-key-here"
    MODEL_NAME: str = "llama-3.3-70b-versatile"

    # PostgreSQL Configuration
    POSTGRES_USER: str = "chatbot_user"
    POSTGRES_PASSWORD: str = "chatbot_password"
    POSTGRES_DB: str = "chatbot_db"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql://chatbot_user:chatbot_password@db:5432/chatbot_db"

    # Application Configuration
    APP_NAME: str = "GPT Chatbot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Rate Limiting
    RATE_LIMIT_RPM: int = 30  # Requests per minute
    MAX_MESSAGES_PER_SESSION: int = 100  # Max messages before context truncation

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached singleton instance of application settings.
    
    Uses lru_cache to ensure the .env file is read only once,
    improving performance across the application lifecycle.
    """
    return Settings()


# Instantiate settings
settings = get_settings()


# Database Configuration
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using them
    echo=settings.DEBUG,  # Log SQL queries in debug mode
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)



# Rate Limiter
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

