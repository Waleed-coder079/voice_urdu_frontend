const recordBtn = document.getElementById("recordBtn");
const status = document.getElementById("status");
const player = document.getElementById("player");

let mediaRecorder = null;
let audioChunks = [];
let micStream = null;

recordBtn.addEventListener("click", async () => {
  try {
    // 🎤 START RECORDING
    if (!mediaRecorder || mediaRecorder.state === "inactive") {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });

      mediaRecorder = new MediaRecorder(micStream);
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunks.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        status.innerText = "Sending audio to server...";

        // Stop mic completely
        micStream.getTracks().forEach(track => track.stop());

        const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
        const reader = new FileReader();

        reader.onloadend = async () => {
          const base64Audio = reader.result.split(",")[1];

          try {
            const response = await fetch("/voice_to_voice", {
              method: "POST",
              headers: {
                "Content-Type": "application/json"
              },
              body: JSON.stringify({ audio_b64: base64Audio })
            });

            const data = await response.json();

            if (data.audio_b64) {
              const audioBytes = Uint8Array.from(
                atob(data.audio_b64),
                c => c.charCodeAt(0)
              );

              const replyBlob = new Blob([audioBytes], { type: "audio/wav" });
              player.src = URL.createObjectURL(replyBlob);
              await player.play();

              status.innerText = "AI Response ready!";
            } else {
              status.innerText = "Error: " + (data.error || "Unknown error");
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
    // 🛑 STOP RECORDING
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
