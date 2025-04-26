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
      // Reset any previous errors
      status.textContent = "Requesting microphone access...";
      status.className = "";
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        } 
      });
      
      // Set up media recorder with specific MIME type if supported
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
          
          // Stop all tracks to release the microphone
          stream.getTracks().forEach(track => track.stop());
          
          if (audioChunks.length === 0) {
            throw new Error("No audio recorded");
          }
          
          // Create blob with the appropriate type
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

      // Start recording
      mediaRecorder.start(100); // Collect data in 100ms chunks
      status.textContent = "🎙️ Recording...";
      recordButton.disabled = true;
      stopButton.disabled = false;

      // Auto-stop after 5s
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

  // 🔄 Upload & display results in chat
  async function sendAudio(blob) {
    const form = new FormData();
    form.append("file", blob, "recording." + (blob.type.includes('webm') ? 'webm' : 'wav'));

    try {
      // Use relative URL for local testing, or full URL for production
      const BASE_URL = window.location.hostname === 'localhost' 
                     ? '' 
                     : 'https://ora-owjy.onrender.com';
      
      status.textContent = "Sending to server...";
      
      const res = await fetch(`${BASE_URL}/predict`, {
        method: "POST",
        body: form,
        headers: { 
          "Accept": "application/json" 
        }
      });

      // Handle non-OK responses
      if (!res.ok) {
        const errorText = await res.text();
        console.error(`Server error (${res.status}):`, errorText);
        throw new Error(`Server returned ${res.status}: ${errorText}`);
      }

      // Parse response
      const data = await res.json();
      
      // Validate response data
      if (!data || !data.probabilities) {
        throw new Error("Invalid response format: missing emotion data");
      }

      // 1) Build the probability sentence
      const parts = Object.entries(data.probabilities)
        .sort((a, b) => b[1] - a[1]) // Sort by descending probability
        .map(([emo, pct]) => `${emo}: ${pct}%`);
      
      const sentence = `You're feeling: ${parts.join(", ")}`;

      // 2) Initialize chat history
      chatHistoryEl.innerHTML = `
        <div class="assistant">📝 ${sentence}</div>
        <br>
        <div class="assistant">🤖 ${data.reply || "How can I help you today?"}</div>
      `;

      // 3) Reveal chat UI and store chat ID
      chatId = data.chat_id;
      chatDiv.classList.remove("hidden");
      status.textContent = "✅ Emotion analysis complete";
      status.className = "success";

    } catch (err) {
      console.error("Upload error:", err);
      status.textContent = `⚠️ Error: ${err.message || "Failed to analyze emotion"}`;
      status.className = "error";
      recordButton.disabled = false;
      
      // Provide more detailed error alert
      alert(`Analysis failed: ${err.message || "Server error"}`);
    }
  }

  // 📨 Send chat messages
  sendBtn.addEventListener("click", sendMessage);
  
  // Also send on Enter key
  userMessage.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  
  async function sendMessage() {
    const text = userMessage.value.trim();
    if (!text || !chatId) return;

    // Append user message
    chatHistoryEl.innerHTML += `<div class="user">🧑 ${text}</div>`;
    userMessage.value = "";
    
    // Scroll to bottom
    chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;

    try {
      // Determine base URL based on environment
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

      // Append assistant reply
      chatHistoryEl.innerHTML += `<div class="assistant">🤖 ${data.reply || "I'm processing your message."}</div>`;
      chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;

    } catch (err) {
      console.error("Chat error:", err);
      chatHistoryEl.innerHTML += `<div class="error">⚠️ Error: ${err.message || "Failed to send message"}</div>`;
      chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
    }
  }
  
  // Initialize UI
  stopButton.disabled = true;
  status.textContent = "Ready to record";
});






