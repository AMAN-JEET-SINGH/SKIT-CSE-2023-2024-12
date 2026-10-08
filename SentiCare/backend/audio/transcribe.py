import os
import httpx
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

def transcribe_audio(audio_file_path: str) -> Dict:
    """
    Transcribe an audio file using the Deepgram API.

    Args:
        audio_file_path (str): Path to a local audio file (.wav, .mp3, etc.)

    Returns:
        dict: {
            "text": str,
            "words": List[{"word": str, "start": float, "end": float}],
            "duration": float,
            "confidence": float
        }
    """
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise EnvironmentError("Missing DEEPGRAM_API_KEY in .env or environment variables")

    try:
        with open(audio_file_path, "rb") as audio:
            buffer_data = audio.read()
        
        url = "https://api.deepgram.com/v1/listen"
        params = {
            "model": "nova-2",
            "smart_format": "true",
            "punctuate": "true",
            "diarize": "false"  
        }
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "audio/wav"  
        }
        
        response = httpx.post(
            url,
            params=params,
            headers=headers,
            content=buffer_data,
            timeout=60.0
        )
        response.raise_for_status()
        
        data = response.json()
        result = data["results"]["channels"][0]["alternatives"][0]

        transcript_text = result.get("transcript", "")
        confidence = result.get("confidence", 0.0)
        
        # Extract per-word timestamps
        words: List[Dict] = []
        if "words" in result:
            words = [
                {
                    "word": w["word"],
                    "start": w["start"],
                    "end": w["end"]
                }
                for w in result["words"]
            ]
        
        duration = words[-1]["end"] if words else 0.0
        
        return {
            "text": transcript_text,
            "words": words,
            "duration": duration,
            "confidence": confidence
        }

    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Deepgram API error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {str(e)}")
