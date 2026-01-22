from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import base64
import logging

from api.runpod_client import voice_to_voice_sync

# -------------------------
# Logging
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s"
)

# -------------------------
# Base directory (project root)
# -------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
    audio_b64: str  # Base64 audio from browser

# -------------------------
# Voice-to-Voice API
# -------------------------
@app.post("/voice_to_voice")
async def voice_to_voice(data: AudioIn):
    try:
        logging.info("voice_to_voice request received")

        if not data.audio_b64:
            logging.error("Empty audio_b64 received")
            return {"error": "Empty audio input"}

        # 🔹 Directly forward browser audio to RunPod
        result = voice_to_voice_sync(data.audio_b64)

        if not result:
            logging.error("Empty response from RunPod")
            return {"error": "Empty RunPod response"}

        # 🔹 Chunked TTS (preferred)
        if "audio_chunks" in result:
            logging.info(
                f"TTS chunks received: {len(result['audio_chunks'])}"
            )
            return {
                "audio_chunks": result["audio_chunks"],
                "transcription": result.get("transcription", ""),
                "llm_response": result.get("llm_response", "")
            }

        # 🔹 Backward compatibility (single audio)
        if "audio_b64" in result:
            logging.warning("Fallback: single audio_b64 response")
            return {
                "audio_chunks": [result["audio_b64"]],
                "transcription": result.get("transcription", ""),
                "llm_response": result.get("llm_response", "")
            }

        logging.error(f"Invalid RunPod response format: {result}")
        return {"error": "Invalid response from voice service"}

    except Exception as e:
        logging.exception("Voice-to-Voice processing failed")
        return {"error": str(e)}
