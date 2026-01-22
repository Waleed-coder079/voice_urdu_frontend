from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import base64
import io
import logging
import sys
from pydub import AudioSegment
from pathlib import Path

# -------------------------
# FFMPEG & FFPROBE CONFIGURATION
# -------------------------
# This logic ensures Vercel finds the binaries in the /api folder
api_dir = Path(__file__).parent.absolute()
ffmpeg_bin = str(api_dir / "ffmpeg")
ffprobe_bin = str(api_dir / "ffprobe")

# 1. Force PATH injection (helps subprocesses find the tools)
os.environ["PATH"] += os.pathsep + str(api_dir)

# 2. Explicitly tell pydub where they are
AudioSegment.converter = ffmpeg_bin
AudioSegment.ffprobe = ffprobe_bin

# Import your runpod client after setting up paths
from api.runpod_client import voice_to_voice_sync

# -------------------------
# Logging
# -------------------------
logging.basicConfig(level=logging.INFO)

# -------------------------
# Base directory setup
# -------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# -------------------------
# FastAPI app
# -------------------------
app = FastAPI()

# Serve static files
static_path = os.path.join(BASE_DIR, "static")
if not os.path.exists(static_path):
    logging.warning(f"Static folder not found at {static_path}")
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
async def index():
    index_file = os.path.join(static_path, "index.html")
    if not os.path.exists(index_file):
        logging.error(f"index.html not found at {index_file}")
        return {"error": "index.html not found"}
    return FileResponse(index_file)

# -------------------------
# Request schema
# -------------------------
class AudioIn(BaseModel):
    audio_b64: str

# -------------------------
# Convert browser audio → WAV
# -------------------------
def convert_to_wav(audio_b64: str, sample_rate=16000) -> bytes:
    try:
        audio_bytes = base64.b64decode(audio_b64)
        
        # We use from_file which relies on ffprobe to detect format (webm/ogg/etc)
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        audio = audio.set_channels(1).set_frame_rate(sample_rate)
        out = io.BytesIO()
        audio.export(out, format="wav")
        return out.getvalue()
    except Exception as e:
        # Logging the specific error helps debug if it's a permission issue or missing file
        logging.error(f"Detailed Conversion Error: {str(e)}")
        raise RuntimeError(f"Audio conversion failed. Error: {str(e)}")

# -------------------------
# Voice-to-Voice API
# -------------------------
@app.post("/voice_to_voice")
async def voice_to_voice(data: AudioIn):
    try:
        # 1️⃣ Convert browser audio to WAV
        wav_bytes = convert_to_wav(data.audio_b64)
        wav_b64 = base64.b64encode(wav_bytes).decode("utf-8")

        # 2️⃣ Call RunPod API
        result = voice_to_voice_sync(wav_b64)

        if not result or "audio_b64" not in result:
            logging.error(f"Invalid RunPod response: {result}")
            return {"error": "Voice processing failed at RunPod"}

        return {
            "audio_b64": result["audio_b64"],
            "sample_rate": result.get("sample_rate", 24000),
            "transcription": result.get("transcription", ""),
            "llm_response": result.get("llm_response", "")
        }

    except Exception as e:
        logging.error(f"Voice-to-Voice endpoint error: {e}")
        return {"error": str(e)}