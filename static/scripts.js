window.addEventListener("DOMContentLoaded", () => {
  let audioChunks = [];
  let mediaRecorder;
  let chatId = null;

  const recordButton  = document.getElementById("recordBtn");
  const stopButton    = document.getElementById("stopBtn");
  const status        = document.getElementById("status");

  // Chat UI elements
  const chatDiv       = document.getElementById("chat");
  const chatHistoryEl = document.getElementById("chatHistory");
  const userMessage   = document.getElementById("userMessage");
  const sendBtn       = document.getElementById("sendBtn");

  // Check if all UI elements exist
  if (!recordButton || !stopButton || !status) {
    console.error("Error: Missing UI elements");
    document.body.innerHTML = "<h2>Error: Missing required UI elements</h2>";
    return;
  }

  // 🎤 Start Recording
  recordButton.addEventListener("click", async () => {
    try {
      status.textContent = "Requesting microphone access...";
      status.className = "";
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        } 
      });
      
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') 
                        ? 'audio/webm' : 'audio/wav';
      
      mediaRecorder = new MediaRecorder(stream, { mimeType });
      audioChunks = [];

      mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) {
          audioChunks.push(e.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        try {
          status.textContent = "Processing audio...";
          
          stream.getTracks().forEach(track => track.stop());
          
          if (audioChunks.length === 0) {
            throw new Error("No audio recorded");
          }
          
          const audioBlob = new Blob(audioChunks, { type: mimeType });
          
          status.textContent = "Uploading to server...";
          await sendAudio(audioBlob);
          
        } catch (err) {
          console.error("Audio processing error:", err);
          status.textContent = "⚠️ Error: " + err.message;
          status.className = "error";
          recordButton.disabled = false;
        }
      };

      mediaRecorder.onerror = (event) => {
        console.error("MediaRecorder error:", event.error);
        status.textContent = "⚠️ Recording error: " + event.error;
        status.className = "error";
        recordButton.disabled = false;
        stopButton.disabled = true;
      };

      mediaRecorder.start(100); 
      status.textContent = "🎙️ Recording...";
      recordButton.disabled = true;
      stopButton.disabled = false;

      setTimeout(() => {
        if (mediaRecorder && mediaRecorder.state === "recording") {
          mediaRecorder.stop();
          stopButton.disabled = true;
          recordButton.disabled = false;
        }
      }, 5000);

    } catch (err) {
      console.error("Microphone access error:", err);
      status.textContent = "⚠️ Error: " + (err.message || "Microphone access denied");
      status.className = "error";
      alert("Please enable microphone access in your browser settings.");
    }
  });

  // ⏹ Stop early
  stopButton.addEventListener("click", () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      status.textContent = "Processing...";
      stopButton.disabled = true;
      recordButton.disabled = false;
    }
  });

  // 🔼 Upload to Uploadcare
  async function uploadToUploadcare(blob) {
    const formData = new FormData();
    formData.append('UPLOADCARE_STORE', '1'); 
    formData.append('UPLOADCARE_PUB_KEY', 'fa6ab5beadb496664775'); // replace this!

    formData.append('file', blob);

    const response = await fetch('https://upload.uploadcare.com/base/', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();
    const fileUrl = `https://ucarecdn.com/${data.file}/`;
    console.log("✅ Uploaded to Uploadcare:", fileUrl);
    return fileUrl;
  }

  // 🔄 Upload & display results in chat
  async function sendAudio(blob) {
    try {
      console.log("📤 Uploading audio to Uploadcare...");
      status.textContent = "Uploading audio...";

      const uploadcareUrl = await uploadToUploadcare(blob);

      console.log("📡 Sending Uploadcare URL to server...");
      status.textContent = "Analyzing emotion...";

      const BASE_URL = window.location.hostname === 'localhost' 
                     ? '' 
                     : 'https://ora-owjy.onrender.com';

      const res = await fetch(`${BASE_URL}/predict`, {
        method: "POST",
        headers: { 
          "Accept": "application/json",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ audio_url: uploadcareUrl })
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.error(`Server error (${res.status}):`, errorText);
        throw new Error(`Server returned ${res.status}: ${errorText}`);
      }

      const data = await res.json();
      
      if (!data || !data.probabilities) {
        throw new Error("Invalid response format: missing emotion data");
      }

      const parts = Object.entries(data.probabilities)
        .sort((a, b) => b[1] - a[1])
        .map(([emo, pct]) => `${emo}: ${pct}%`);

      const sentence = `You're feeling: ${parts.join(", ")}`;

      chatHistoryEl.innerHTML = `
        <div class="assistant">📝 ${sentence}</div>
        <br>
        <div class="assistant">🤖 ${data.reply || "How can I help you today?"}</div>
      `;

      chatId = data.chat_id;
      chatDiv.classList.remove("hidden");
      status.textContent = "✅ Emotion analysis complete";
      status.className = "success";

    } catch (err) {
      console.error("Upload error:", err);
      status.textContent = `⚠️ Error: ${err.message || "Failed to analyze emotion"}`;
      status.className = "error";
      recordButton.disabled = false;
      alert(`Analysis failed: ${err.message || "Server error"}`);
    }
  }

  // 📨 Send chat messages
  sendBtn.addEventListener("click", sendMessage);
  
  userMessage.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  
  async function sendMessage() {
    const text = userMessage.value.trim();
    if (!text || !chatId) return;

    chatHistoryEl.innerHTML += `<div class="user">🧑 ${text}</div>`;
    userMessage.value = "";
    chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;

    try {
      const BASE_URL = window.location.hostname === 'localhost' 
                     ? '' 
                     : 'https://ora-owjy.onrender.com';

      const res = await fetch(`${BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, message: text })
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Server error (${res.status}): ${errorText}`);
      }

      const data = await res.json();
      
      if (data.error) throw new Error(data.error);

      chatHistoryEl.innerHTML += `<div class="assistant">🤖 ${data.reply || "I'm processing your message."}</div>`;
      chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;

    } catch (err) {
      console.error("Chat error:", err);
      chatHistoryEl.innerHTML += `<div class="error">⚠️ Error: ${err.message || "Failed to send message"}</div>`;
      chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
    }
  }

  stopButton.disabled = true;
  status.textContent = "Ready to record";
});




