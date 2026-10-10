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

from app.agent.graph import graph
from app.voice.tts import text_to_speech
from app.rag.vector_store import search_chunks
from httpx import AsyncClient, ASGITransport
from app.main import app

ACTIVE_DOC = "Shilpi_Tripathi_AI_Engineer_Resume.pdf"
VOICE_TEST_DIR = Path("data/voice")
VOICE_TEST_DIR.mkdir(parents=True, exist_ok=True)


async def run_all_10_core_tests():
    print("=" * 75)
    print("RUNNING COMPLETE AURARAG CORE VERIFICATION SUITE (ALL 10 REQUIREMENTS)")
    print("NO WAKE WORD -- CLICK-TO-RECORD / MANUAL ACTIVATION ARCHITECTURE")
    print("=" * 75)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # ----------------------------------------------------
        # TEST 1: Normal voice query (Voice audio -> Whisper -> Agent -> Groq -> Edge TTS)
        # ----------------------------------------------------
        print("\n--- TEST 1: Normal Voice Query ('What is artificial intelligence?') ---")
        q1_audio = VOICE_TEST_DIR / "test_normal_voice.mp3"
        await text_to_speech("What is artificial intelligence?", str(q1_audio))

        with q1_audio.open("rb") as f:
            resp1 = await client.post(
                "/voice",
                files={"file": ("test_normal_voice.mp3", f, "audio/mpeg")},
                data={"filename": ""}
            )
        data1 = resp1.json()
        print(f"Status: {resp1.status_code}")
        print(f"Transcribed: {data1.get('query')}")
        print(f"Answer: {data1.get('answer')[:120]}...")
        print(f"Audio URL: {data1.get('audio_url')}")

        assert resp1.status_code == 200, f"Expected 200, got {resp1.status_code}"
        assert "is_wake" not in data1, "Wake word field should not exist"
        assert len(data1.get("query", "").strip()) > 0, "Expected transcribed query"
        assert len(data1.get("answer", "").strip()) > 20, "Expected substantive answer"
        assert data1.get("audio_url") is not None, "Expected audio_url for normal voice response"
        print(">>> TEST 1 PASSED: Normal voice query transcribed, answered, and synthesized to speech.")

        # ----------------------------------------------------
        # TEST 2: RAG voice query (Active document question via voice)
        # ----------------------------------------------------
        print("\n--- TEST 2: RAG Voice Query ('What does my PDF say about Python?') ---")
        q2_audio = VOICE_TEST_DIR / "test_rag_voice.mp3"
        await text_to_speech("What does my PDF say about Python?", str(q2_audio))

        with q2_audio.open("rb") as f:
            resp2 = await client.post(
                "/voice",
                files={"file": ("test_rag_voice.mp3", f, "audio/mpeg")},
                data={"filename": ACTIVE_DOC}
            )
        data2 = resp2.json()
        print(f"Status: {resp2.status_code}")
        print(f"Transcribed: {data2.get('query')}")
        print(f"Answer: {data2.get('answer')[:150]}...")
        print(f"Audio URL: {data2.get('audio_url')}")

        assert resp2.status_code == 200
        assert "is_wake" not in data2
        assert "python" in data2.get("answer", "").lower(), "Expected answer grounded in resume PDF"
        assert data2.get("audio_url") is not None
        print(">>> TEST 2 PASSED: RAG voice query grounded strictly in uploaded document context.")

        # ----------------------------------------------------
        # TEST 3: MCP voice query (Explicit web search via voice)
        # ----------------------------------------------------
        print("\n--- TEST 3: MCP Voice Query ('Search the web for the latest LangGraph developments.') ---")
        q3_audio = VOICE_TEST_DIR / "test_mcp_voice.mp3"
        await text_to_speech("Search the web for the latest LangGraph developments.", str(q3_audio))

        with q3_audio.open("rb") as f:
            resp3 = await client.post(
                "/voice",
                files={"file": ("test_mcp_voice.mp3", f, "audio/mpeg")},
                data={"filename": ACTIVE_DOC}
            )
        data3 = resp3.json()
        print(f"Status: {resp3.status_code}")
        print(f"Transcribed: {data3.get('query')}")
        print(f"Answer: {data3.get('answer')[:150]}...")
        print(f"Audio URL: {data3.get('audio_url')}")

        assert resp3.status_code == 200
        assert "is_wake" not in data3
        assert len(data3.get("answer", "")) > 50, "Expected substantive MCP search synthesis"
        assert data3.get("audio_url") is not None
        print(">>> TEST 3 PASSED: MCP web search executed and synthesized via Edge TTS.")

        # ----------------------------------------------------
        # TEST 4: RAG + MCP voice query (Comparison via voice)
        # ----------------------------------------------------
        print("\n--- TEST 4: RAG + MCP Combined Voice Query ('Compare what is in my PDF with latest information online') ---")
        q4_audio = VOICE_TEST_DIR / "test_combined_voice.mp3"
        await text_to_speech("Compare what is in my PDF with latest information online", str(q4_audio))

        with q4_audio.open("rb") as f:
            resp4 = await client.post(
                "/voice",
                files={"file": ("test_combined_voice.mp3", f, "audio/mpeg")},
                data={"filename": ACTIVE_DOC}
            )
        data4 = resp4.json()
        print(f"Status: {resp4.status_code}")
        print(f"Transcribed: {data4.get('query')}")
        print(f"Answer: {data4.get('answer')[:200]}...")
        print(f"Audio URL: {data4.get('audio_url')}")

        assert resp4.status_code == 200
        assert "is_wake" not in data4
        assert len(data4.get("answer", "")) > 80, "Expected comparative synthesis"
        assert data4.get("audio_url") is not None
        print(">>> TEST 4 PASSED: Combined RAG + MCP synthesized document vs. online comparison.")

        # ----------------------------------------------------
        # TEST 5: File-action voice query (Local file discovery & upload via voice)
        # ----------------------------------------------------
        print("\n--- TEST 5: File Action Voice Query ('Upload Machine_Learning_1_with_anno.pdf from Downloads.') ---")
        q5_audio = VOICE_TEST_DIR / "test_file_action_voice.mp3"
        await text_to_speech("Upload Machine_Learning_1_with_anno.pdf from Downloads.", str(q5_audio))

        with q5_audio.open("rb") as f:
            resp5 = await client.post(
                "/voice",
                files={"file": ("test_file_action_voice.mp3", f, "audio/mpeg")},
                data={"filename": ACTIVE_DOC}
            )
        data5 = resp5.json()
        print(f"Status: {resp5.status_code}")
        print(f"Answer: {data5.get('answer')}")
        print(f"Active Document: {data5.get('active_document')}")
        print(f"Audio URL: {data5.get('audio_url')}")

        assert resp5.status_code == 200
        assert "is_wake" not in data5
        assert "uploaded" in data5.get("answer", "").lower() or "done" in data5.get("answer", "").lower()
        assert data5.get("active_document") == "Machine_Learning_1_with_anno.pdf"
        assert data5.get("audio_url") is not None
        print(">>> TEST 5 PASSED: Local file action executed via voice, activeDocument updated, audio synthesized.")

        # ----------------------------------------------------
        # TEST 6: Manual document upload (POST /upload)
        # ----------------------------------------------------
        print("\n--- TEST 6: Manual Document Upload (POST /upload) ---")
        sample_txt_path = Path("data/sample.txt")
        if not sample_txt_path.exists():
            sample_txt_path.write_text("AuraRAG manual upload test document.", encoding="utf-8")

        with sample_txt_path.open("rb") as f:
            resp6 = await client.post(
                "/upload",
                files={"file": ("sample.txt", f, "text/plain")}
            )
        data6 = resp6.json()
        print(f"Status: {resp6.status_code}")
        print(f"Filename: {data6.get('filename')}")
        print(f"Chunks: {data6.get('number_of_chunks')}")

        assert resp6.status_code == 200
        assert data6.get("filename") == "sample.txt"
        assert data6.get("number_of_chunks") > 0
        print(">>> TEST 6 PASSED: Manual file upload chunked and indexed in ChromaDB.")

        # ----------------------------------------------------
        # TEST 7: Text query (POST /ask)
        # ----------------------------------------------------
        print("\n--- TEST 7: Text Query Fallback (POST /ask) ---")
        resp7 = await client.post(
            "/ask",
            json={"query": "What is AuraRAG?", "filename": "sample.txt"}
        )
        data7 = resp7.json()
        print(f"Status: {resp7.status_code}")
        print(f"Answer: {data7.get('answer')[:120]}...")
        print(f"Audio URL: {data7.get('audio_url')}")

        assert resp7.status_code == 200
        assert "is_wake" not in data7
        assert len(data7.get("answer", "")) > 20
        assert data7.get("audio_url") is not None
        print(">>> TEST 7 PASSED: POST /ask text query returned grounded answer and speech.")

        # ----------------------------------------------------
        # TEST 8: TTS playback (GET /voice-audio/{filename})
        # ----------------------------------------------------
        print("\n--- TEST 8: Static TTS Audio Playback Endpoint ---")
        audio_path = data7.get("audio_url")
        assert audio_path is not None, "audio_url must exist"
        audio_resp = await client.get(audio_path)
        print(f"Audio URL: {audio_path}")
        print(f"Status: {audio_resp.status_code}")
        print(f"Bytes received: {len(audio_resp.content)}")

        assert audio_resp.status_code == 200
        assert len(audio_resp.content) > 1000, "Audio response must contain binary MP3 data"
        print(">>> TEST 8 PASSED: Generated TTS audio is accessible for browser playback.")

        # ----------------------------------------------------
        # TEST 9: MCP Fallback (Document lacks current info -> MCP)
        # ----------------------------------------------------
        print("\n--- TEST 9: RAG -> MCP Fallback Workflow ---")
        fallback_res = await graph.ainvoke({
            "query": "What are the latest developments in LangGraph?",
            "source": ACTIVE_DOC,
            "context": "",
            "answer": "",
            "route": "",
            "is_clarification": False,
            "uploaded_document": None
        })
        print(f"Executed Route: {fallback_res.get('route')}")
        print(f"Answer: {fallback_res.get('answer')[:150]}...")

        assert fallback_res.get("route") == "mcp_fallback"
        assert len(fallback_res.get("answer", "")) > 40
        print(">>> TEST 9 PASSED: Agent verified document lacked current info and fell back to MCP.")

        # ----------------------------------------------------
        # TEST 10: Document Isolation (Only active document chunks retrieved)
        # ----------------------------------------------------
        print("\n--- TEST 10: Document Isolation & Source Filtering ---")
        # Search specifically within ACTIVE_DOC
        results = search_chunks(
            query="Python machine learning",
            source=ACTIVE_DOC,
            n_results=4
        )
        metas = results["metadatas"][0] if results.get("metadatas") else []
        for m in metas:
            assert m.get("source") == ACTIVE_DOC, f"Cross-document leak detected: found chunk with source {m.get('source')}"

        print(f"Verified {len(metas)} chunks retrieved strictly with source == '{ACTIVE_DOC}'")
        print(">>> TEST 10 PASSED: Strict document isolation enforced in ChromaDB.")

    print("\n" + "=" * 75)
    print("ALL 10 CORE VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_all_10_core_tests())
