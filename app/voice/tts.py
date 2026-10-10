import asyncio
import edge_tts


# Voice used by AuraRAG
VOICE = "en-US-AriaNeural"


async def text_to_speech(
    text: str,
    output_path: str
):
    """
    Convert text into speech
    and save it as an MP3 file.
    Includes retry logic for transient network blips.
    """
    clean_text = text.strip()
    if not clean_text:
        clean_text = "I'm listening."

    max_retries = 3
    last_err = None

    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(
                clean_text,
                VOICE
            )
            await communicate.save(output_path)
            return output_path
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                await asyncio.sleep(1.0)

    raise last_err