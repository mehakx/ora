// static/scripts.js
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

  const BASE_URL = "https://ora-owjy.onrender.com"; // Change if needed

  recordButton.addEventListener("click", async () => {
    try {
      status.textContent = "Requesting microphone access...";
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/wav';
      mediaRecorder = new MediaRecorder(stream, { mimeType });
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunks.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        try {
          status.textContent = "Processing audio...";
          stream.getTracks().forEach((track) => track.stop());

          if (audioChunks.length === 0) {
            throw new Error("No audio recorded");
          }

          const audioBlob = new Blob(audioChunks, { type: mimeType });
          status.textContent = "Uploading audio to server...";
          const audioUrl = await uploadToServer(audioBlob);

          status.textContent = "Analyzing emotion...";
          await analyzeEmotion(audioUrl);

        } catch (err) {
          console.error(err);
          status.textContent = `⚠️ Error: ${err.message}`;
          status.className = "error";
          recordButton.disabled = false;
        }
      };

      mediaRecorder.start();
      status.textContent = "🎤 Recording...";
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
      console.error(err);
      alert("Microphone access denied.");
      status.textContent = `⚠️ Error: ${err.message}`;
      status.className = "error";
    }
  });

  stopButton.addEventListener("click", () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      status.textContent = "Processing audio...";
      stopButton.disabled = true;
      recordButton.disabled = false;
    }
  });

  async function uploadToServer(blob) {
    const formData = new FormData();
    formData.append("file", blob);

    const response = await fetch(`${BASE_URL}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Upload failed: ${errorText}`);
    }

    const data = await response.json();
    console.log("✅ File uploaded, server URL:", data.url);
    return data.url;
  }

  async function analyzeEmotion(audioUrl) {
    const res = await fetch(`${BASE_URL}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio_url: audioUrl }),
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Server error: ${errorText}`);
    }

    const data = await res.json();
    if (!data || !data.probabilities) {
      throw new Error("Invalid emotion analysis response");
    }

    const parts = Object.entries(data.probabilities)
      .sort((a, b) => b[1] - a[1])
      .map(([emo, pct]) => `${emo}: ${pct}%`);
    const sentence = `You're feeling: ${parts.join(", ")}`;

    chatHistoryEl.innerHTML = `
      <div class="assistant">📝 ${sentence}</div><br>
      <div class="assistant">🤖 ${data.reply || "How can I help you today?"}</div>
    `;

    chatId = data.chat_id;
    chatDiv.classList.remove("hidden");
    status.textContent = "✅ Emotion analysis complete";
    status.className = "success";
  }

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

    chatHistoryEl.innerHTML += `<div class="user">🧑‍💻 ${text}</div>`;
    userMessage.value = "";
    chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;

    try {
      const res = await fetch(`${BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, message: text }),
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Chat server error: ${errorText}`);
      }

      const data = await res.json();
      chatHistoryEl.innerHTML += `<div class="assistant">🤖 ${data.reply || "I'm thinking..."}</div>`;
      chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;

    } catch (err) {
      console.error(err);
      chatHistoryEl.innerHTML += `<div class="error">⚠️ ${err.message}</div>`;
      chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
    }
  }

  stopButton.disabled = true;
  status.textContent = "Ready to record!";
});
