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
    return;
  }

  const BASE_URL = "https://ora-owjy.onrender.com";

  // Start recording
  recordButton.addEventListener("click", async () => {
    try {
      status.textContent = "🎤 Recording...";
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/wav';
      mediaRecorder = new MediaRecorder(stream, { mimeType });
      audioChunks = [];

      mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        if (audioChunks.length === 0) {
          status.textContent = "⚠️ No audio recorded";
          return;
        }
        const audioBlob = new Blob(audioChunks, { type: mimeType });
        await analyzeAudio(audioBlob);
      };

      mediaRecorder.start();
      recordButton.disabled = true;
      stopButton.disabled = false;

      // Auto-stop after 5 seconds
      setTimeout(() => {
        if (mediaRecorder.state === "recording") {
          mediaRecorder.stop();
          stopButton.disabled = true;
          recordButton.disabled = false;
        }
      }, 5000);

    } catch (err) {
      console.error("Recording error:", err);
      status.textContent = "⚠️ " + err.message;
    }
  });

  // Stop early
  stopButton.addEventListener("click", () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      stopButton.disabled = true;
      recordButton.disabled = false;
    }
  });

  // Send audio directly to Hume via /analyze-audio
  async function analyzeAudio(blob) {
    try {
      status.textContent = "🔄 Analyzing audio...";
      const form = new FormData();
      form.append("audio", blob, "recording.webm");

      const res = await fetch(`${BASE_URL}/analyze-audio`, {
        method: "POST",
        body: form
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Server error (${res.status}): ${text}`);
      }

      const data = await res.json();
      const { emotion, probabilities, reply, chat_id } = data;

      // Display results
      const probsArr = Object.entries(probabilities)
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
    try {
      const resp = await fetch(`${BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, message: text })
      });
      if (!resp.ok) throw new Error(await resp.text());
      const chatData = await resp.json();
      chatHistoryEl.innerHTML += `<div class="assistant">🤖 ${chatData.reply}</div>`;
    } catch (err) {
      console.error("Chat error:", err);
    }
  }

  stopButton.disabled = true;
  status.textContent = "Ready to record";
});
