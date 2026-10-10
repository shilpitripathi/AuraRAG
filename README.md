# AuraRAG — Voice-First AI Agent with Agentic RAG and MCP Web Search

AuraRAG is a voice-first AI assistant application that allows users to interact with documents and external knowledge using manual push-to-talk voice recording. It combines local Whisper Speech-to-Text (STT), LangGraph agent orchestration, ChromaDB vector retrieval, external Model Context Protocol (MCP) search, Groq LLM inference, and Edge TTS speech synthesis.

---

## Architecture Flow

```
User Clicks Microphone (Manual Activation)
               │
               ▼
     WebM Audio Recording
               │
               ▼
       Whisper STT (Local)
               │
               ▼
     LangGraph AuraRAG Agent
 ┌─────────────┼───────────────┬─────────────────┐
 │             │               │                 │
 ▼             ▼               ▼                 ▼
RAG       MCP Search       RAG + MCP        File Action
(ChromaDB) (Parallel.ai) (Hybrid Synth)  (Local Discovery)
 └─────────────┼───────────────┴─────────────────┘
               │
               ▼
          Groq LLM
               │
               ▼
       Edge TTS Synthesis
               │
               ▼
      Audio Playback (MP3)
```

---

## Key Features

- **Push-to-Talk Voice Interaction**: Click-to-record voice workflow with zero background wake listening.
- **Strict Document Grounding**: Semantic retrieval via ChromaDB vector database with source isolation.
- **Autonomous MCP Fallback**: Automatically searches the web when uploaded documents do not contain the answer.
- **Combined RAG + Online Synthesis**: Compares document contents against live online search results.
- **Controlled File Discovery**: Safe ingestion of user-approved documents from local folders in local mode.
- **Hardened Production Endpoints**: Size limits, path traversal protection, CORS controls, and auto-purging temporary audio files.

---

## Environment Variables

### Backend Configuration (`.env`)

| Variable | Description | Default | Required |
| :--- | :--- | :--- | :--- |
| `GROQ_API_KEY` | API Key for Groq LLM inference | None | **Yes** |
| `GROQ_MODEL` | LLM model identifier on Groq | `openai/gpt-oss-20b` | No |
| `MCP_SERVER_URL` | Endpoint for Parallel.ai MCP server | `https://search.parallel.ai/mcp` | No |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins | `http://localhost:5173,http://127.0.0.1:5173` | **Yes** (in Prod) |
| `CHROMA_PERSIST_DIR`| Storage directory for ChromaDB embeddings | `chroma_db` | No |
| `MAX_UPLOAD_SIZE_MB`| Maximum allowed document upload size (MB) | `20` | No |
| `DEPLOYMENT_ENV` | `development` or `production` | `development` | No |
| `ENABLE_LOCAL_FILE_ACCESS` | Enable local filesystem browsing (`false` in cloud) | `true` | No |

### Frontend Configuration (`frontend/.env`)

| Variable | Description | Default | Required |
| :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8000` | **Yes** (in Prod) |

---

## Local Development Setup

### 1. Prerequisites
- Python 3.11 or 3.12
- Node.js 18+ and npm
- FFmpeg installed and available on system `PATH` (required for Whisper & audio processing)

### 2. Backend Setup
```bash
# Activate virtual environment
source .venv/bin/activate  # Or on Windows: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your GROQ_API_KEY

# Start backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Start development server
npm run dev
```

---

## Production Deployment Guide

### Backend Production Startup
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```
*Note: Due to PyTorch and Whisper in-memory model weights, run with 1 worker per container/instance or allocate sufficient memory (minimum 2GB RAM).*

### Frontend Production Build
```bash
cd frontend
npm run build
```
Deploy the generated `frontend/dist` directory to any static hosting provider (e.g., Vercel, Netlify, Cloudflare Pages, AWS S3 / CloudFront).

---

## Deployment Architecture & Limitations

1. **Single-Tenant / Private Instance**: ChromaDB uses a single local collection with document-name filtering. For multi-tenant hosting, isolate instances or provide user-scoped namespaces.
2. **Localhost vs. Cloud Filesystem**: In cloud hosting (Render, Railway, Fly.io, AWS), set `ENABLE_LOCAL_FILE_ACCESS=false` and `DEPLOYMENT_ENV=production`. This gracefully prompts users to upload files via the web UI rather than searching the container's nonexistent local user folders.
3. **Hardware Requirements**: Whisper STT (`base` model) and SentenceTransformers run on CPU/GPU. Ensure at least 2GB RAM is provisioned on host instances.
