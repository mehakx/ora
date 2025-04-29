 // static/scripts.js

window.addEventListener("DOMContentLoaded", () => {
  let audioChunks = [];
  let mediaRecorder;
  let chatId = null;

  const recordButton = document.getElementById("recordBtn");
  const stopButton = document.getElementById("stopBtn");
  const status = document.getElementById("status");
  const chatDiv = document.getElementById("chat");
  const chatHistoryEl = document.getElementById("chatHistory");
  const userMessage = document.getElementById("userMessage");
  const sendBtn = document.getElementById("sendBtn");

  if (!recordButton || !stopButton || !status) {
    console.error("Missing UI elements");
    document.body.innerHTML = "<h2>Error: Missing required UI elements</h2>";
    return;
  }

  const BASE_URL = "https://ora-owjy.onrender.com";

  // Start recording
  recordButton.addEventListener("click", async () => {
    try {
      status.textContent = "Requesting microphone access...";
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
          echoCancellation: true, 
          noiseSuppression: true, 
          sampleRate: 44100 
        } 
      });
      
      status.textContent = "🎤 Recording...";
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/wav';
      mediaRecorder = new MediaRecorder(stream, { mimeType });
      audioChunks = [];

      mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        try {
          status.textContent = "Processing audio...";
          stream.getTracks().forEach(t => t.stop());
          
          if (audioChunks.length === 0) {
            status.textContent = "⚠️ No audio recorded";
            recordButton.disabled = false;
            return;
          }
          
          const audioBlob = new Blob(audioChunks, { type: mimeType });
          await analyzeAudio(audioBlob);
        } catch (err) {
          console.error("Audio processing error:", err);
          status.textContent = "⚠️ Error: " + err.message;
          recordButton.disabled = false;
        }
      };

      mediaRecorder.start(100);
      recordButton.disabled = true;
      stopButton.disabled = false;

      // Auto-stop after 5 seconds
      setTimeout(() => {
        if (mediaRecorder && mediaRecorder.state === "recording") {
          mediaRecorder.stop();
          stopButton.disabled = true;
          recordButton.disabled = false;
        }
      }, 5000);

    } catch (err) {
      console.error("Recording error:", err);
      status.textContent = "⚠️ " + err.message;
      alert("Please enable microphone access in your browser settings.");
    }
  });

  // Stop early
  stopButton.addEventListener("click", () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      stopButton.disabled = true;
      recordButton.disabled = false;
      status.textContent = "Processing...";
    }
  });

  // Send audio directly to Hume via /analyze-audio
  async function analyzeAudio(blob) {
    try {
      status.textContent = "🔄 Analyzing audio...";
      
      console.log("📤 Sending audio for analysis...");
      const form = new FormData();
      form.append("audio", blob, "recording.webm");

      const res = await fetch(`${BASE_URL}/analyze-audio`, {
        method: "POST",
        body: form
      });
      
      console.log(`Response status: ${res.status}`);
      
      if (!res.ok) {
        const text = await res.text();
        console.error(`Server error: ${text}`);
        throw new Error(`Server error (${res.status}): ${text}`);
      }

      const data = await res.json();
      console.log("Analysis response:", data);
      
      if (!data || !data.emotion) {
        throw new Error("Invalid response format from server");
      }
      
      const { emotion, probabilities, reply, chat_id } = data;

      // Display results
      const probsArr = Object.entries(probabilities)
        .sort((a, b) => b[1] - a[1])
        .map(([emo, pct]) => `${emo}: ${pct}%`)
        .join(', ');
        
      chatHistoryEl.innerHTML = `
        <div class="assistant">📝 You're feeling: ${probsArr}</div>
        <div class="assistant">🤖 ${reply}</div>
      `;
      
      chatId = chat_id;
      chatDiv.classList.remove("hidden");
      status.textContent = "✅ Analysis complete";

    } catch (err) {
      console.error("Analysis error:", err);
      status.textContent = "⚠️ " + err.message;
      recordButton.disabled = false;
    }
  }

  // Chat follow-up
  sendBtn.addEventListener("click", sendMessage);
  userMessage.addEventListener("keypress", e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  async function sendMessage() {
    const text = userMessage.value.trim();
    if (!text || !chatId) return;
    
    chatHistoryEl.innerHTML += `<div class="user">🧑‍💻 ${text}</div>`;
    userMessage.value = "";
    chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
    
    try {
      const resp = await fetch(`${BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, message: text })
      });
      
      if (!resp.ok) {
        const errorText = await resp.text();
        throw new Error(errorText);
      }
      
      const chatData = await resp.json();
      chatHistoryEl.innerHTML += `<div class="assistant">🤖 ${chatData.reply}</div>`;
      chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
      
    } catch (err) {
      console.error("Chat error:", err);
      chatHistoryEl.innerHTML += `<div class="error">⚠️ Error: ${err.message}</div>`;
      chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
    }
  }

  stopButton.disabled = true;
  status.textContent = "Ready to record";
});
