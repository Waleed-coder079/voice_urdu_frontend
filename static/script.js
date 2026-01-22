const recordBtn = document.getElementById("recordBtn");
const status = document.getElementById("status");
const player = document.getElementById("player");

let mediaRecorder = null;
let audioChunks = [];
let micStream = null;

// 🔊 TTS playback state
let audioQueue = [];
let isPlaying = false;
let bufferTimer = null;
const BUFFER_DELAY_MS = 400; // 300–500ms sweet spot

// ===============================
// Audio playback helpers (TTS WAV)
// ===============================
function playNextChunk() {
  if (audioQueue.length === 0) {
    isPlaying = false;
    status.innerText = "AI response completed";
    return;
  }

  isPlaying = true;
  const blob = audioQueue.shift();
  player.src = URL.createObjectURL(blob);

  player.onended = () => playNextChunk();

  player.play().catch(err => {
    console.error("Playback error:", err);
    playNextChunk();
  });
}

function enqueueAudioChunk(base64Audio) {
  const audioBytes = Uint8Array.from(
    atob(base64Audio),
    c => c.charCodeAt(0)
  );

  // 🔊 TTS OUTPUT IS WAV (correct)
  const blob = new Blob([audioBytes], { type: "audio/wav" });
  audioQueue.push(blob);

  if (!isPlaying && !bufferTimer) {
    bufferTimer = setTimeout(() => {
      bufferTimer = null;
      playNextChunk();
    }, BUFFER_DELAY_MS);
  }
}

// ===============================
// Recording logic (WEBM)
// ===============================
recordBtn.addEventListener("click", async () => {
  try {
    if (!mediaRecorder || mediaRecorder.state === "inactive") {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mimeType = "audio/webm;codecs=opus";

      mediaRecorder = new MediaRecorder(micStream, { mimeType });
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunks.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        status.innerText = "Sending audio to server...";

        // Reset playback state
        audioQueue = [];
        isPlaying = false;
        if (bufferTimer) {
          clearTimeout(bufferTimer);
          bufferTimer = null;
        }

        micStream.getTracks().forEach(track => track.stop());

        // ✅ REAL FORMAT: WEBM
        const audioBlob = new Blob(audioChunks, { type: mimeType });
        const reader = new FileReader();

        reader.onloadend = async () => {
          const base64Audio = reader.result.split(",")[1];

          try {
            const response = await fetch("/voice_to_voice", {
              method: "POST",
              headers: {
                "Content-Type": "application/json"
              },
              body: JSON.stringify({
                audio_b64: base64Audio,
                mime_type: mimeType   // ✅ IMPORTANT
              })
            });

            const data = await response.json();

            if (data.audio_chunks && Array.isArray(data.audio_chunks)) {
              status.innerText = "AI is speaking...";
              data.audio_chunks.forEach(chunk => enqueueAudioChunk(chunk));

            } else if (data.audio_b64) {
              enqueueAudioChunk(data.audio_b64);

            } else {
              status.innerText = "Error: Invalid audio response";
            }

          } catch (err) {
            console.error(err);
            status.innerText = "Fetch failed: " + err.message;
          }
        };

        reader.readAsDataURL(audioBlob);
      };

      mediaRecorder.start();
      recordBtn.innerText = "■ Stop Recording";
      status.innerText = "Recording... Speak now";
    }

    else if (mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      recordBtn.innerText = "🎤 Start Recording";
      status.innerText = "Processing...";
    }

  } catch (err) {
    console.error(err);
    status.innerText = "Microphone error: " + err.message;
  }
});
