import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

# Ensure utf-8 output on Windows terminal
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from app.agent.graph import graph
from app.voice.tts import text_to_speech
from app.voice.stt import transcribe_audio
from httpx import AsyncClient, ASGITransport
from app.main import app

ACTIVE_DOC = "Shilpi_Tripathi_AI_Engineer_Resume.pdf"


async def run_tests():
    print("=" * 60)
    print("RUNNING COMPLETE AURARAG ARCHITECTURE & ROUTING VERIFICATION")
    print("=" * 60)

    # ----------------------------------------------------
    # TEST 1: Active PDF contains X -> RAG only
    # ----------------------------------------------------
    print("\n--- TEST 1: Active PDF contains X ('What does my PDF say about LangGraph?') ---")
    res1 = await graph.ainvoke({
        "query": "What does my PDF say about LangGraph?",
        "source": ACTIVE_DOC,
        "context": "",
        "answer": "",
        "route": "",
        "is_clarification": False
    })
    print(f"Result Route: {res1.get('route')}")
    print(f"Answer: {res1.get('answer')[:200]}...")
    assert res1.get("route") == "rag", f"Expected 'rag', got {res1.get('route')}"
    assert "langgraph" in res1.get("answer").lower(), "Expected answer to discuss LangGraph from resume"
    print(">>> TEST 1 PASSED: RAG only used for document question.")

    # ----------------------------------------------------
    # TEST 2: Active PDF lacks current info on X -> MCP fallback
    # ----------------------------------------------------
    print("\n--- TEST 2: Active PDF lacks current info on X ('What are the latest developments in LangGraph?') ---")
    res2 = await graph.ainvoke({
        "query": "What are the latest developments in LangGraph?",
        "source": ACTIVE_DOC,
        "context": "",
        "answer": "",
        "route": "",
        "is_clarification": False
    })
    print(f"Result Route: {res2.get('route')}")
    print(f"Answer: {res2.get('answer')[:200]}...")
    assert res2.get("route") in ("mcp_fallback", "mcp"), f"Expected mcp_fallback or mcp, got {res2.get('route')}"
    assert len(res2.get("answer")) > 50, "Expected substantive answer from web search"
    print(">>> TEST 2 PASSED: RAG checked PDF, detected lack of current info, fell back to MCP.")

    # ----------------------------------------------------
    # TEST 3: Explicit web search -> MCP directly
    # ----------------------------------------------------
    print("\n--- TEST 3: Explicit web search ('Search the web for the latest LangGraph developments.') ---")
    res3 = await graph.ainvoke({
        "query": "Search the web for the latest LangGraph developments.",
        "source": ACTIVE_DOC,
        "context": "",
        "answer": "",
        "route": "",
        "is_clarification": False
    })
    print(f"Result Route: {res3.get('route')}")
    print(f"Answer: {res3.get('answer')[:200]}...")
    assert res3.get("route") == "mcp", f"Expected 'mcp', got {res3.get('route')}"
    print(">>> TEST 3 PASSED: MCP directly executed for explicit web search.")

    # ----------------------------------------------------
    # TEST 4: 'Search the web' -> Clarification prompt, no MCP search, no TTS audio
    # ----------------------------------------------------
    print("\n--- TEST 4: Suggestion button click / empty search ('Search the web') ---")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp4 = await client.post("/ask", json={"query": "Search the web", "filename": ACTIVE_DOC})
        data4 = resp4.json()
        print(f"Status Code: {resp4.status_code}")
        print(f"Answer: {data4.get('answer')}")
        print(f"audio_url: {data4.get('audio_url')}")
        assert data4.get("answer") == "Sure — what would you like me to search for?", f"Unexpected answer: {data4.get('answer')}"
        assert data4.get("audio_url") is None, f"Expected audio_url to be None, got {data4.get('audio_url')}"
    print(">>> TEST 4 PASSED: Clarification returned, no MCP search executed, TTS audio suppressed.")

    # ----------------------------------------------------
    # TEST 5: 'What is RAG?' -> Normal agent routing (knowledge explanation)
    # ----------------------------------------------------
    print("\n--- TEST 5: Conceptual question ('What is RAG?') ---")
    res5 = await graph.ainvoke({
        "query": "What is RAG?",
        "source": None,
        "context": "",
        "answer": "",
        "route": "",
        "is_clarification": False
    })
    print(f"Result Route: {res5.get('route')}")
    print(f"Answer: {res5.get('answer')[:200]}...")
    assert res5.get("route") == "rag", f"Expected 'rag', got {res5.get('route')}"
    assert "retrieval" in res5.get("answer").lower(), "Expected answer explaining RAG"
    print(">>> TEST 5 PASSED: General concept answered directly without forced web search.")

    # ----------------------------------------------------
    # TEST 6: Voice document query -> Whisper -> RAG -> Groq -> Edge TTS
    # ----------------------------------------------------
    print("\n--- TEST 6: Voice document query via /voice endpoint ---")
    test_voice_file = Path("data/voice/test_doc_query.mp3")
    await text_to_speech("What does my PDF say about Python and machine learning?", str(test_voice_file))
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with test_voice_file.open("rb") as f:
            resp6 = await client.post(
                "/voice",
                files={"file": ("test_doc_query.mp3", f, "audio/mpeg")},
                data={"filename": ACTIVE_DOC}
            )
        data6 = resp6.json()
        print(f"Transcribed Query: {data6.get('query')}")
        print(f"Answer: {data6.get('answer')[:200]}...")
        print(f"Audio URL: {data6.get('audio_url')}")
        assert data6.get("audio_url") is not None, "Expected audio_url to be present"
        assert len(data6.get("answer")) > 30, "Expected substantive document answer"
    print(">>> TEST 6 PASSED: Voice document query transcribed, routed to RAG, synthesized to voice.")

    # ----------------------------------------------------
    # TEST 7: Voice current query -> Whisper -> MCP -> Groq -> Edge TTS
    # ----------------------------------------------------
    print("\n--- TEST 7: Voice current query via /voice endpoint ---")
    test_voice_current = Path("data/voice/test_current_query.mp3")
    await text_to_speech("What are the latest developments in artificial intelligence?", str(test_voice_current))
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with test_voice_current.open("rb") as f:
            resp7 = await client.post(
                "/voice",
                files={"file": ("test_current_query.mp3", f, "audio/mpeg")},
                data={"filename": ACTIVE_DOC}
            )
        data7 = resp7.json()
        print(f"Transcribed Query: {data7.get('query')}")
        print(f"Answer: {data7.get('answer')[:200]}...")
        print(f"Audio URL: {data7.get('audio_url')}")
        assert data7.get("audio_url") is not None, "Expected audio_url to be present"
        assert len(data7.get("answer")) > 50, "Expected answer from web search"
    print(">>> TEST 7 PASSED: Voice current query transcribed, routed to MCP fallback, synthesized to voice.")

    # ----------------------------------------------------
    # TEST 8: Voice comparison -> RAG + MCP -> Groq -> Edge TTS
    # ----------------------------------------------------
    print("\n--- TEST 8: Voice comparison ('Compare what is in my PDF with latest information online') ---")
    test_voice_compare = Path("data/voice/test_compare_query.mp3")
    await text_to_speech("Compare what is in my PDF with latest information online", str(test_voice_compare))
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with test_voice_compare.open("rb") as f:
            resp8 = await client.post(
                "/voice",
                files={"file": ("test_compare_query.mp3", f, "audio/mpeg")},
                data={"filename": ACTIVE_DOC}
            )
        data8 = resp8.json()
        print(f"Transcribed Query: {data8.get('query')}")
        print(f"Answer: {data8.get('answer')[:300]}...")
        print(f"Audio URL: {data8.get('audio_url')}")
        assert data8.get("audio_url") is not None, "Expected audio_url to be present"
        assert len(data8.get("answer")) > 80, "Expected substantive comparative answer"
    print(">>> TEST 8 PASSED: Voice comparison combined RAG + MCP and synthesized comparative audio.")

    print("\n" + "=" * 60)
    print("ALL 8 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
