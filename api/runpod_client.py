import os
import requests
import httpx
import asyncio

# ===============================
# CONFIG
# ===============================

ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
BASE_URL = f"https://im9z11oiydq2ij-8000.proxy.runpod.net"

HEADERS = {
    "Content-Type": "application/json",
}

# ===============================
# SYNC CLIENT
# ===============================

def call_runpod_sync(endpoint: str, payload: dict) -> dict:
    """Call RunPod endpoint synchronously (direct HTTP POST)"""
    url = f"{BASE_URL}/{endpoint}"
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers=HEADERS,
            timeout=300
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error calling {endpoint}: {str(e)}")
        return {}

# ===============================
# ASYNC CLIENT
# ===============================

async def call_runpod_async(endpoint: str, payload: dict) -> dict:
    """Call RunPod endpoint asynchronously (direct HTTP POST)"""
    url = f"{BASE_URL}/{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                url,
                json=payload,
                headers=HEADERS
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Async error calling {endpoint}: {str(e)}")
        # Fallback to sync
        return call_runpod_sync(endpoint, payload)

# ===============================
# Voice-to-Voice CALLS
# ===============================

async def voice_to_voice_async(audio_b64: str) -> dict:
    """
    Call the unified RunPod endpoint for voice-to-voice.
    Input format stays the same: {"audio_b64": "..."}
    """
    return await call_runpod_async("voice_to_voice", {"audio_b64": audio_b64})

def voice_to_voice_sync(audio_b64: str) -> dict:
    """
    Call the unified RunPod endpoint synchronously.
    Input format stays the same: {"audio_b64": "..."}
    """
    return call_runpod_sync("voice_to_voice", {"audio_b64": audio_b64})
