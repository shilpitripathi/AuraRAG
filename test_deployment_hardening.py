import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_upload_empty_file():
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/upload",
        files={"file": ("empty.txt", empty_file, "text/plain")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_upload_invalid_extension():
    fake_exe = io.BytesIO(b"MZ\x90\x00")
    response = client.post(
        "/upload",
        files={"file": ("malicious.exe", fake_exe, "application/octet-stream")}
    )
    assert response.status_code == 400
    assert "unsupported file type" in response.json()["detail"].lower()

def test_upload_oversized_file(monkeypatch):
    # Set max upload size to 1MB for testing
    import app.main
    monkeypatch.setattr(app.main, "MAX_UPLOAD_SIZE_BYTES", 1024 * 1024)
    big_file = io.BytesIO(b"A" * (1024 * 1024 + 10))
    response = client.post(
        "/upload",
        files={"file": ("large.txt", big_file, "text/plain")}
    )
    assert response.status_code == 413
    assert "exceeds maximum allowed" in response.json()["detail"].lower()

def test_voice_empty_audio():
    empty_audio = io.BytesIO(b"")
    response = client.post(
        "/voice",
        files={"file": ("empty.webm", empty_audio, "audio/webm")}
    )
    assert response.status_code == 200
    assert "no audio received" in response.json()["answer"].lower()

def test_voice_audio_path_traversal():
    response = client.get("/voice-audio/../main.py")
    # Path traversal should fail with 400 (regex validation) or 403
    assert response.status_code in [400, 403, 404]

def test_voice_audio_invalid_filename():
    response = client.get("/voice-audio/invalid$name.mp3")
    assert response.status_code == 400

def test_voice_audio_nonexistent_file():
    response = client.get("/voice-audio/nonexistent_123456789.mp3")
    assert response.status_code == 404

if __name__ == "__main__":
    print("Testing GET /health...")
    test_health_check()
    print("Testing empty upload...")
    test_upload_empty_file()
    print("Testing invalid extension upload...")
    test_upload_invalid_extension()
    print("Testing oversized upload...")
    import app.main
    class MonkeyPatch:
        def setattr(self, obj, attr, val):
            setattr(obj, attr, val)
    test_upload_oversized_file(MonkeyPatch())
    print("Testing empty voice...")
    test_voice_empty_audio()
    print("Testing voice audio path traversal...")
    test_voice_audio_path_traversal()
    print("Testing voice audio invalid filename...")
    test_voice_audio_invalid_filename()
    print("Testing voice audio nonexistent file...")
    test_voice_audio_nonexistent_file()
    print("ALL HARDENING TESTS PASSED SUCCESSFULLY!")

