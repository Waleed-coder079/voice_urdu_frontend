from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import base64
import io
import logging
from pydub import AudioSegment  # pip install pydub

from api.runpod_client import voice_to_voice_sync

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# -------------------------
# Serve static files (Vercel serverless path)
# -------------------------
app.mount("/static", StaticFiles(directory="../static"), name="static")

# -------------------------
# Serve frontend HTML
# -------------------------
@app.get("/")
async def index():
    return FileResponse(os.path.join("../static", "index.html"))

# -------------------------
# Request schema
# -------------------------
class AudioIn(BaseModel):
    audio_b64: str  # base64 from browser (webm/ogg)

# -------------------------
# Convert browser audio → WAV
# -------------------------
def convert_to_wav(audio_b64: str, sample_rate=16000) -> bytes:
    audio_bytes = base64.b64decode(audio_b64)
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    audio = audio.set_channels(1).set_frame_rate(sample_rate)
    out = io.BytesIO()
    audio.export(out, format="wav")
    return out.getvalue()

# -------------------------
# Voice-to-Voice API
# -------------------------
@app.post("/voice_to_voice")
async def voice_to_voice(data: AudioIn):
    try:
        # 1️⃣ Convert browser audio to WAV
        wav_bytes = convert_to_wav(data.audio_b64)
        wav_b64 = base64.b64encode(wav_bytes).decode("utf-8")

        # 2️⃣ Call unified RunPod endpoint
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
