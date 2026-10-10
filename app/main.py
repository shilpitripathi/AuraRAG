import asyncio
import logging
import os
import re
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.agent.graph import graph
from app.rag.chunker import split_text
from app.rag.loader import load_document
from app.rag.vector_store import add_chunks
from app.voice.stt import transcribe_audio
from app.voice.tts import text_to_speech

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("aurarag")

# --------------------------------------------------
# APP SETUP
# --------------------------------------------------

app = FastAPI(
    title="AuraRAG",
    description="Voice-first AI RAG Agent API",
    version="1.0.0"
)

# CORS Configuration
raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
)
allowed_origins = [orig.strip() for orig in raw_origins.split(",") if orig.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

VOICE_DIR = Path("data/voice")
VOICE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


# --------------------------------------------------
# AUDIO CLEANUP UTILITY
# --------------------------------------------------

def cleanup_old_audio_files(max_age_seconds: int = 1800, max_files: int = 50):
    """
    Remove audio files older than max_age_seconds (default 30 mins)
    or retain only the most recent max_files to prevent disk leaks.
    """
    try:
        now = time.time()
        for f in VOICE_DIR.glob("*.webm"):
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass

        mp3_files = [f for f in VOICE_DIR.glob("*.mp3") if f.is_file()]
        for f in mp3_files:
            try:
                if now - f.stat().st_mtime > max_age_seconds:
                    f.unlink(missing_ok=True)
            except Exception:
                pass

        remaining_mp3 = sorted(
            [f for f in VOICE_DIR.glob("*.mp3") if f.is_file()],
            key=lambda x: x.stat().st_mtime
        )
        if len(remaining_mp3) > max_files:
            for old_file in remaining_mp3[:-max_files]:
                try:
                    old_file.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Error during audio cleanup: {e}")


# --------------------------------------------------
# HEALTH & ROOT
# --------------------------------------------------

@app.get("/health")
def health_check():
    """
    Lightweight health check endpoint for monitoring & deployment platforms.
    Does not require Groq, Whisper, or external services.
    """
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "message": "AuraRAG is running"
    }


# --------------------------------------------------
# SECURE AUDIO PLAYBACK
# --------------------------------------------------

@app.get("/voice-audio/{filename}")
async def get_voice_audio(filename: str):
    """
    Securely serve generated audio responses.
    Prevents path traversal, directory scanning, and arbitrary filesystem access.
    """
    # Filename must match standard safe alphanumeric UUID format with .mp3
    if not re.match(r"^[a-zA-Z0-9_\-]+\.mp3$", filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid audio filename."
        )

    audio_file = (VOICE_DIR / filename).resolve()
    voice_dir_resolved = VOICE_DIR.resolve()

    # Guard against directory traversal
    try:
        if not audio_file.is_relative_to(voice_dir_resolved):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied."
            )
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    if not audio_file.exists() or not audio_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found."
        )

    return FileResponse(
        path=str(audio_file),
        media_type="audio/mpeg",
        filename=filename
    )


# --------------------------------------------------
# HARDENED DOCUMENT UPLOAD
# --------------------------------------------------

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):
    """
    Securely ingest documents into ChromaDB.
    Validates file extensions, prevents path traversal, caps upload size,
    and guards against empty or unparseable files.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload."
        )

    # Sanitize filename (strip directory components)
    raw_name = Path(file.filename).name
    # Keep only safe characters: letters, digits, spaces, dots, dashes, underscores
    clean_name = re.sub(r'[^a-zA-Z0-9_\-\. ]+', '_', raw_name).strip()
    if not clean_name:
        clean_name = f"document_{uuid.uuid4().hex[:8]}"

    ext = Path(clean_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    file_path = DATA_DIR / clean_name

    # Stream file to disk while enforcing max upload size
    total_bytes = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    try:
        with file_path.open("wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                    buffer.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"File exceeds maximum allowed upload size of {MAX_UPLOAD_SIZE_MB}MB."
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        file_path.unlink(missing_ok=True)
        logger.error(f"Error saving uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file."
        )

    if total_bytes == 0:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    # Parse document text
    try:
        text = load_document(str(file_path))
    except Exception as e:
        file_path.unlink(missing_ok=True)
        logger.error(f"Document parsing failure for '{clean_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to read or parse '{clean_name}'. File may be corrupt, password-protected, or invalid."
        )

    if not text or not text.strip():
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The document '{clean_name}' contains no readable text. (Scanned image-only PDFs without an OCR layer are not supported)."
        )

    # Split document into chunks
    chunks = split_text(text)
    if not chunks:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not generate readable text chunks from the document."
        )

    # Store chunks in ChromaDB
    try:
        stored_chunks = add_chunks(chunks, clean_name)
    except Exception as e:
        logger.error(f"ChromaDB storage failure for '{clean_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to index document in the vector store."
        )

    logger.info(f"Successfully uploaded and indexed '{clean_name}' ({stored_chunks} chunks)")

    return {
        "filename": clean_name,
        "message": "Document stored successfully",
        "number_of_chunks": stored_chunks
    }


# --------------------------------------------------
# QUESTION REQUEST (TEXT FALLBACK)
# --------------------------------------------------

class QuestionRequest(BaseModel):
    query: str
    filename: str | None = None


@app.post("/ask")
async def ask(request: QuestionRequest):
    """
    Direct text query fallback.
    Routes through the LangGraph Agent and returns synthesized answer + speech.
    """
    query_clean = request.query.strip() if request.query else ""
    if not query_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query text cannot be empty."
        )

    doc_source = request.filename.strip() if request.filename and request.filename.strip() else None

    try:
        result = await graph.ainvoke({
            "query": query_clean,
            "source": doc_source,
            "context": "",
            "answer": "",
            "route": "",
            "is_clarification": False,
            "uploaded_document": None
        })
    except Exception as e:
        logger.error(f"Agent error in /ask: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing query with the AI service."
        )

    answer = result.get("answer", "No answer could be generated.")
    is_clarification = result.get("is_clarification", False)
    new_active_doc = result.get("uploaded_document") or doc_source

    # Generate speech
    audio_url = None
    if not is_clarification:
        try:
            cleanup_old_audio_files()
            output_filename = f"{uuid.uuid4().hex}.mp3"
            output_path = VOICE_DIR / output_filename
            await text_to_speech(answer, str(output_path))
            audio_url = f"/voice-audio/{output_filename}"
        except Exception as e:
            logger.error(f"TTS generation error in /ask: {e}")

    return {
        "question": query_clean,
        "answer": answer,
        "audio_url": audio_url,
        "active_document": new_active_doc
    }


# --------------------------------------------------
# HARDENED VOICE PIPELINE
# --------------------------------------------------

@app.post("/voice")
async def voice_input(
    file: UploadFile = File(...),
    filename: str | None = Form(None)
):
    """
    Manual-activation voice pipeline:
    1. Receive voice recording (.webm)
    2. Transcribe via Whisper STT
    3. Delete temporary audio recording immediately
    4. Validate transcribed text
    5. Route to AuraRAG Agent (RAG / MCP / RAG+MCP / File Action)
    6. Synthesize answer with Edge TTS
    7. Return answer and playable audio URL
    """
    input_filename = f"rec_{uuid.uuid4().hex}.webm"
    input_path = VOICE_DIR / input_filename

    # Read and buffer voice audio with size guard (max 15MB)
    MAX_VOICE_BYTES = 15 * 1024 * 1024
    total_bytes = 0

    try:
        with input_path.open("wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_VOICE_BYTES:
                    buffer.close()
                    input_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="Voice recording exceeds maximum allowed size (15MB)."
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        input_path.unlink(missing_ok=True)
        logger.error(f"Error saving voice recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to receive audio data."
        )

    doc_source = filename.strip() if filename and filename.strip() else None

    if total_bytes == 0:
        input_path.unlink(missing_ok=True)
        return {
            "query": "",
            "answer": "No audio received. Please click the microphone and speak.",
            "audio_url": None,
            "active_document": doc_source
        }

    # Transcribe audio with Whisper
    query_raw = ""
    try:
        query_raw = transcribe_audio(str(input_path))
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return {
            "query": "",
            "answer": "Sorry, I had trouble processing that voice recording. Please click the microphone and try again.",
            "audio_url": None,
            "active_document": doc_source
        }
    finally:
        # Guarantee cleanup of uploaded microphone audio
        try:
            input_path.unlink(missing_ok=True)
        except Exception:
            pass

    query_clean = query_raw.strip() if query_raw else ""

    if not query_clean:
        return {
            "query": "",
            "answer": "I didn't catch that. Please click the microphone and try speaking again.",
            "audio_url": None,
            "active_document": doc_source
        }

    # Execute AuraRAG Agent
    try:
        result = await graph.ainvoke({
            "query": query_clean,
            "source": doc_source,
            "context": "",
            "answer": "",
            "route": "",
            "is_clarification": False,
            "uploaded_document": None
        })
    except Exception as e:
        logger.error(f"Agent error in /voice for query '{query_clean}': {e}")
        return {
            "query": query_clean,
            "answer": "I encountered an error processing your question with the AI service. Please try again.",
            "audio_url": None,
            "active_document": doc_source
        }

    answer = result.get("answer", "No answer could be generated.")
    is_clarification = result.get("is_clarification", False)
    new_active_doc = result.get("uploaded_document") or doc_source

    # Text → Speech via Edge TTS
    audio_url = None
    if not is_clarification:
        try:
            cleanup_old_audio_files()
            output_filename = f"{uuid.uuid4().hex}.mp3"
            output_path = VOICE_DIR / output_filename

            await text_to_speech(answer, str(output_path))
            audio_url = f"/voice-audio/{output_filename}"
        except Exception as e:
            logger.error(f"TTS generation error in /voice: {e}")

    return {
        "query": query_clean,
        "answer": answer,
        "audio_url": audio_url,
        "active_document": new_active_doc
    }