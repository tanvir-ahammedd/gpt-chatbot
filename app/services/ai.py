"""
AI service for LLM integration with Groq API.

Handles all communication with the Groq LLM API, including
prompt construction, response generation, and error handling.
Uses the Groq SDK for efficient API calls with Llama models.
"""

import logging
from typing import Generator, Optional

from groq import Groq, APIError, RateLimitError, APIConnectionError

from app.config import get_settings


# Configure logger for this module
logger = logging.getLogger(__name__)

# Load application settings
settings = get_settings()

# System prompt that defines the AI assistant's personality and behavior
SYSTEM_PROMPT = """You are a helpful, friendly, and knowledgeable AI assistant. 
You provide clear, accurate, and well-structured responses. 
You remember the context of our conversation and refer back to previous messages when relevant.
If you're unsure about something, you say so honestly rather than making up information.
Keep your responses concise but thorough."""


class AIService:
    """
    Service for generating AI responses using the Groq API.
    
    Integrates with Groq's fast inference API to generate
    context-aware responses using conversation history.
    Supports both standard (blocking) and streaming response modes.
    
    Attributes:
        client: Groq SDK client instance.
        model: The LLM model name to use for generation.
    """

    def __init__(self):
        """
        Initialize the AI service with Groq client configuration.
        
        Raises:
            ValueError: If GROQ_API_KEY is not configured.
        """
        if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your-groq-api-key-here":
            raise ValueError(
                "GROQ_API_KEY is not configured. "
                "Please set a valid API key in your .env file."
            )

        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.MODEL_NAME
        logger.info(f"AI Service initialized with model: {self.model}")

    def generate_response(
        self,
        user_message: str,
        conversation_history: list[dict],
    ) -> str:
        """
        Generate an AI response based on the user's message and conversation history.
        
        Constructs the full message context (system prompt + history + new message)
        and sends it to the Groq API for response generation.
        
        Args:
            user_message: The current message from the user.
            conversation_history: List of previous messages as dicts
                                  with 'role' and 'content' keys.
        
        Returns:
            The AI-generated response text.
            
        Raises:
            Exception: If the API call fails after error handling.
        """
        try:
            # Build the full message list for the LLM
            messages = self._build_messages(user_message, conversation_history)

            # Call the Groq API
            chat_completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,       # Balanced creativity vs consistency
                max_tokens=1024,       # Reasonable response length
                top_p=1,               # Nucleus sampling
                stream=False,          # Non-streaming for simplicity
            )

            # Extract and return the response text
            response_text = chat_completion.choices[0].message.content
            logger.info(
                f"Generated response: {len(response_text)} chars, "
                f"model: {chat_completion.model}"
            )
            return response_text

        except RateLimitError as e:
            logger.warning(f"Groq API rate limit reached: {e}")
            return (
                "I'm currently experiencing high demand. "
                "Please wait a moment and try again."
            )

        except APIConnectionError as e:
            logger.error(f"Failed to connect to Groq API: {e}")
            return (
                "I'm having trouble connecting to my AI service. "
                "Please check your internet connection and try again."
            )

        except APIError as e:
            logger.error(f"Groq API error: {e.status_code} - {e.message}")
            return (
                "I encountered an error while generating a response. "
                "Please try again shortly."
            )

        except Exception as e:
            logger.error(f"Unexpected error in AI service: {e}", exc_info=True)
            return (
                "An unexpected error occurred. "
                "Please try again or start a new session."
            )

    def generate_response_stream(
        self,
        user_message: str,
        conversation_history: list[dict],
    ) -> Generator[str, None, None]:
        """
        Stream an AI response token by token using Groq's streaming API.
        
        Yields text chunks as they arrive from the LLM, enabling real-time
        Server-Sent Events (SSE) delivery to the client.
        
        Args:
            user_message: The current message from the user.
            conversation_history: List of previous messages as dicts
                                  with 'role' and 'content' keys.
                                  
        Yields:
            Individual text chunks (tokens) from the AI response.
        """
        try:
            messages = self._build_messages(user_message, conversation_history)

            # Enable streaming mode
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                top_p=1,
                stream=True,
            )

            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:  # Skip empty chunks
                    yield content

        except RateLimitError as e:
            logger.warning(f"Groq streaming rate limit reached: {e}")
            yield "I'm currently experiencing high demand. Please wait a moment and try again."

        except APIConnectionError as e:
            logger.error(f"Groq streaming connection error: {e}")
            yield "I'm having trouble connecting to my AI service. Please check your connection."

        except APIError as e:
            logger.error(f"Groq streaming API error: {e.status_code} - {e.message}")
            yield "I encountered an error while generating a response. Please try again shortly."

        except Exception as e:
            logger.error(f"Unexpected streaming error: {e}", exc_info=True)
            yield "An unexpected error occurred. Please try again or start a new session."

    def _build_messages(
        self,
        user_message: str,
        conversation_history: list[dict],
    ) -> list[dict]:
        """
        Build the complete message list for the Groq API call.
        
        Combines the system prompt, conversation history, and the
        new user message into the format expected by the API.
        
        Args:
            user_message: The current message from the user.
            conversation_history: Previous messages in the session.
            
        Returns:
            List of message dicts ready for the API call.
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        # Add conversation history for context
        if conversation_history:
            messages.extend(conversation_history)

        # Add the current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    def health_check(self) -> bool:
        """
        Verify that the Groq API is reachable and the API key is valid.
        
        Sends a minimal request to test connectivity.
        
        Returns:
            True if the API is accessible, False otherwise.
        """
        try:
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            logger.error(f"AI health check failed: {e}")
            return False


# Singleton instance for app-wide use
ai_service = AIService()

