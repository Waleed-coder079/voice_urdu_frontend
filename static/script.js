const recordBtn = document.getElementById("recordBtn");
const status = document.getElementById("status");
const player = document.getElementById("player");

let mediaRecorder = null;
let audioChunks = [];
let micStream = null;

// ===============================
// Audio playback helper (Single File)
// ===============================
function playAudio(base64Audio) {
    try {
        const audioBytes = Uint8Array.from(
            atob(base64Audio),
            c => c.charCodeAt(0)
        );

        const blob = new Blob([audioBytes], { type: "audio/wav" });
        const url = URL.createObjectURL(blob);
        
        player.src = url;
        status.innerText = "AI is speaking...";
        
        player.play().catch(err => {
            console.error("Playback error:", err);
            status.innerText = "Error: Playback failed";
        });

        player.onended = () => {
            status.innerText = "AI response completed";
            URL.revokeObjectURL(url); // Clean up memory
        };
    } catch (err) {
        console.error("Encoding error:", err);
        status.innerText = "Error: Could not decode audio";
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

                // Stop the mic tracks
                micStream.getTracks().forEach(track => track.stop());

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
                                format: "webm" // Matches your VoiceRequest schema
                            })
                        });

                        if (!response.ok) {
                            const errData = await response.json();
                            throw new Error(errData.detail || "Server error");
                        }

                        const data = await response.json();
                        console.log("Received audio_b64 length:", data.audio_b64.length);

                        // Handle single audio_b64 field from older model
                        if (data.audio_b64) {
                            playAudio(data.audio_b64);
                        } else {
                            status.innerText = "Error: No audio response from AI";
                        }

                    } catch (err) {
                        console.error(err);
                        status.innerText = "Request failed: " + err.message;
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