import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

# Ensure utf-8 output on Windows terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.voice.tts import text_to_speech

VOICE_DIR = Path("data/voice")
VOICE_DIR.mkdir(parents=True, exist_ok=True)

async def test_simple_voice_rag():
    print("=" * 60)
    print("TESTING SIMPLIFIED VOICE RAG PIPELINE")
    print("=" * 60)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        print("\n1. Testing GET /")
        resp = await client.get("/")
        print(f"Status: {resp.status_code}, Body: {resp.json()}")
        assert resp.status_code == 200
        assert resp.json().get("message") == "AuraRAG is running"
        print("✓ Health check passed")

        # 2. Upload document
        print("\n2. Testing POST /upload")
        test_file_path = Path("data/sample.txt")
        if not test_file_path.exists():
            test_file_path.write_text("AuraRAG is an AI Voice RAG Assistant designed for rapid knowledge retrieval.")
        
        with test_file_path.open("rb") as f:
            resp = await client.post(
                "/upload",
                files={"file": ("sample.txt", f, "text/plain")}
            )
        print(f"Status: {resp.status_code}, Body: {resp.json()}")
        assert resp.status_code == 200
        upload_data = resp.json()
        assert upload_data.get("filename") == "sample.txt"
        assert upload_data.get("number_of_chunks", 0) > 0
        print("✓ Document upload passed")

        # 3. Test /ask fallback
        print("\n3. Testing POST /ask (Text fallback)")
        resp = await client.post(
            "/ask",
            json={"query": "What is AuraRAG?", "filename": "sample.txt"}
        )
        print(f"Status: {resp.status_code}, Body: {resp.json()}")
        assert resp.status_code == 200
        ask_data = resp.json()
        assert "question" in ask_data
        assert "answer" in ask_data
        assert "is_wake" not in ask_data, "Error: 'is_wake' found in /ask response!"
        assert ask_data.get("audio_url") is not None
        print(f"Answer: {ask_data['answer'][:80]}...")
        print(f"Audio URL: {ask_data['audio_url']}")
        print("✓ POST /ask passed (no is_wake, TTS audio generated)")

        # 4. Test /voice pipeline
        print("\n4. Testing POST /voice")
        # Generate a test audio file using Edge TTS
        test_voice_file = VOICE_DIR / "test_input_question.mp3"
        await text_to_speech("What is AuraRAG?", str(test_voice_file))
        assert test_voice_file.exists() and test_voice_file.stat().st_size > 0

        with test_voice_file.open("rb") as f:
            resp = await client.post(
                "/voice",
                files={"file": ("test_input_question.mp3", f, "audio/mpeg")},
                data={"filename": "sample.txt"}
            )
        print(f"Status: {resp.status_code}, Body: {resp.json()}")
        assert resp.status_code == 200
        voice_data = resp.json()
        assert "query" in voice_data
        assert "answer" in voice_data
        assert "audio_url" in voice_data
        assert "is_wake" not in voice_data, "Error: 'is_wake' found in /voice response!"
        assert voice_data.get("audio_url") is not None
        print(f"Transcribed query: {voice_data['query']}")
        print(f"Answer: {voice_data['answer'][:80]}...")
        print(f"Audio URL: {voice_data['audio_url']}")
        print("✓ POST /voice passed (transcription -> RAG -> TTS -> audio_url, no is_wake)")

        # 5. Test static audio serving
        audio_url = voice_data["audio_url"]
        audio_resp = await client.get(audio_url)
        assert audio_resp.status_code == 200
        assert len(audio_resp.content) > 0
        print(f"✓ Static audio accessible: {audio_url} ({len(audio_resp.content)} bytes)")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_simple_voice_rag())
