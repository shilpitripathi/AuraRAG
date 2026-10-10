import whisper


# Load Whisper once when the application starts
model = whisper.load_model("base")


def transcribe_audio(file_path: str) -> str:
    """
    Convert microphone audio into text.
    """

    result = model.transcribe(file_path)

    return result["text"]