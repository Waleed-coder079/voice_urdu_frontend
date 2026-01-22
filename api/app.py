from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import base64
import io
import logging
from pydub import AudioSegment

from api.runpod_client import voice_to_voice_sync


AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
# -------------------------
# Logging
# -------------------------
logging.basicConfig(level=logging.INFO)

# -------------------------
# Base directory (project root) for Vercel serverless
# -------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root

# -------------------------
# FastAPI app
# -------------------------
app = FastAPI()

# -------------------------
# Serve static files
# -------------------------
static_path = os.path.join(BASE_DIR, "static")
if not os.path.exists(static_path):
    logging.warning(f"Static folder not found at {static_path}")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# -------------------------
# Serve index.html
# -------------------------
index_file = os.path.join(static_path, "index.html")
@app.get("/")
async def index():
    if not os.path.exists(index_file):
        logging.error(f"index.html not found at {index_file}")
        return {"error": "index.html not found"}
    return FileResponse(index_file)

# -------------------------
# Request schema
# -------------------------
class AudioIn(BaseModel):
    audio_b64: str  # base64 from browser (webm/ogg)

# -------------------------
# Convert browser audio → WAV
# -------------------------
def convert_to_wav(audio_b64: str, sample_rate=16000) -> bytes:
    try:
        audio_bytes = base64.b64decode(audio_b64)
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        audio = audio.set_channels(1).set_frame_rate(sample_rate)
        out = io.BytesIO()
        audio.export(out, format="wav")
        return out.getvalue()
    except Exception as e:
        logging.error(f"Error converting audio to WAV: {e}")
        raise RuntimeError("Audio conversion failed. Ensure ffmpeg is available.")

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

        if "audio_b64" not in result:
            logging.error(f"Invalid RunPod response: {result}")
            return {"error": "Voice processing failed"}

        return {
            "audio_b64": result["audio_b64"],
            "sample_rate": result.get("sample_rate", 24000),
            "transcription": result.get("transcription", ""),
            "llm_response": result.get("llm_response", "")
        }

    except Exception as e:
        logging.error(f"Voice-to-Voice error: {e}")
        return {"error": str(e)}
