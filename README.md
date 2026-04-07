# GPT Chatbot — Persistent AI Conversational Assistant

A ChatGPT-style conversational AI chatbot with persistent message storage, built with **FastAPI**, **Groq LLM**, and **PostgreSQL**.

## 🚀 Overview

This application provides a RESTful API for multi-turn AI conversations. It uses:
- **FastAPI**: High-performance backend framework.
- **Groq API**: Lightning-fast LLM inference (Llama 3.1 models).
- **PostgreSQL**: Persistent storage for session-isolated chat history.
- **Docker Compose**: One-command orchestration for the entire stack.

---

## 🛠️ Tech Stack

- **Language**: Python 3.12
- **Framework**: FastAPI
- **LLM API**: Groq (Llama-3.1-8b-instant)
- **Database**: PostgreSQL 16
- **Validation**: Pydantic v2
- **ORM**: SQLAlchemy
- **Rate Limiting**: slowapi (per-IP, configurable via `.env`)
- **Containerization**: Docker & Docker Compose

---

## 🚦 Quick Start (Docker)

### 1. Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/) installed.
- A **Groq API Key** (get one for free at [Groq Cloud](https://console.groq.com/keys)).

### 2. Configure Environment
Create a `.env` file from the example:
```bash
cp .env.example .env
```
Open `.env` and add your `GROQ_API_KEY`.

### 3. Run the Application
Start the services:
```bash
docker-compose up --build
```
The API will be available at `http://localhost:8000`.
The interactive API documentation is at `http://localhost:8000/docs`.

---

## 🔗 API Reference

All endpoints are rate-limited per client IP. Exceeding the limit returns **HTTP 429 Too Many Requests**.

### 1. Chat
`POST /chat` — **30 req/min** (configurable via `RATE_LIMIT_RPM`)
- **Body**: `{"session_id": "string", "message": "string"}`
- **Response**: Returns the AI's reply. History is automatically managed.

### 2. Streaming Chat (SSE)
`POST /chat/stream` — **30 req/min**
- **Body**: `{"session_id": "string", "message": "string"}`
- **Response**: Streams the AI's reply token by token via Server-Sent Events.

### 3. History
`GET /history/{session_id}` — **60 req/min**
- **Response**: Returns the full ordered history for the specific session.

### 4. Clear History
`DELETE /history/{session_id}` — **30 req/min**
- **Response**: Resets/deletes the memory for that session.

### 5. Health Check
`GET /health` — **60 req/min**
- **Response**: Status of the API and connectivity to Groq.

---

## 📂 Project Structure

```text
├── app/
│   ├── config.py           # App configuration, DB engine, and rate limiter
│   ├── main.py             # FastAPI entry point & middleware setup
│   ├── models/
│   │   └── schemas.py      # Pydantic schemas & SQLAlchemy DB models
│   ├── routes/
│   │   └── chat.py         # HTTP endpoints for chat, history, and health
│   └── services/
│       ├── ai.py           # Groq LLM integration and streaming logic
│       └── memory.py       # PostgreSQL database CRUD operations
├── tests/
│   └── ...                 # Test scripts
├── .env.example            # Environment variables template
├── docker-compose.yml      # Multi-container orchestration
├── Dockerfile              # App container image definition
├── README.md               # Project documentation
└── requirements.txt        # Python dependencies
```

---

## 🏗️ Architecture Notes

### 1. Key Design Decisions
- **FastAPI for Async Performance**: Chosen for its native asynchronous capabilities and automatic OpenAPI documentation. Perfect for handling potentially long-running LLM API calls without blocking the server.
- **Dependency Injection**: SQLAlchemy Database sessions (`get_db`) are injected into routes. This ensures resources are properly acquired and automatically closed per request, eliminating connection leaks.
- **PostgreSQL over In-Memory**: An in-memory dict fails under multi-worker deployments (e.g., gunicorn) and container restarts. PostgreSQL guarantees true production persistence and scalable session isolation.
- **Groq API Integration**: Selected for its incredibly low latency with Llama models, significantly improving UX for a chatbot compared to traditional, slower endpoints.

### 2. Separation of Concerns
The project follows a clean, modular structure strictly isolating domains:
- **Routes (`app/routes/`)**: Exclusively handles HTTP request parsing, validation, and orchestrating the services.
- **Services (`app/services/`)**: 
    - `ai.py`: Purely encapsulates LLM prompt logic, streaming generation, and Groq SDK integration.
    - `memory.py`: Centralizes all database interactions.
- **Models (`app/models/`)**: 
    - `schemas.py`: Consolidates strictly typed Pydantic structures mapping API requests/responses, as well as the SQLAlchemy table definitions mirroring the database shape.
- **Config (`app/config.py`)**: Stores application-wide settings, the centralized DB connection engine, and rate-limiting setup.

    
### 3. API Usage Flow & Mechanics
- **Interaction**: A client interacts primarily with `POST /chat` (or `/chat/stream`), supplying a `session_id`. Every message—both user and AI—is inserted into the `chat_messages` table attached to this ID.
- **Context Management**: On every request, the backend fetches the ordered history for the provided `session_id`. To prevent token exhaustion and control costs, the context is truncated dynamically via the `MAX_MESSAGES_PER_SESSION` configuration variable before being formatted for the LLM. 
- **Rate Limiting Protection**: `slowapi` enforces limits per client IP via ASGI middleware, returning `429 Too Many Requests` early in the request pipeline if boundaries are crossed.

---

## 🎥 Video Demonstration
[Link to your Video Demo here]

---

## 🌟 Bonus Features Implemented
- [x] **Persistent Storage**: Uses PostgreSQL instead of in-memory maps.
- [x] **Context Truncation**: Smart limit on message history sent to the LLM.
- [x] **Rate Limiting**: Per-IP rate limiting on all endpoints via slowapi.
- [x] **Streaming Responses**: Token-by-token API responses using Server-Sent Events (SSE).
- [x] **Health Metrics**: Real-time status reporting of LLM and DB status.
- [x] **Modular Structure**: Clean architecture following production standards.

