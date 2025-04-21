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

  // 🎤 Start Recording
  recordButton.addEventListener("click", async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
      mediaRecorder.onstop = async () => {
        status.textContent = "Uploading…";
        await sendAudio(new Blob(audioChunks, { type: "audio/wav" }));
      };

      mediaRecorder.start();
      status.textContent    = "🎙️ Recording…";
      recordButton.disabled = true;
      stopButton.disabled   = false;

      // Auto‑stop after 5s
      setTimeout(() => {
        if (mediaRecorder.state === "recording") {
          mediaRecorder.stop();
          stopButton.disabled   = true;
          recordButton.disabled = false;
        }
      }, 5000);

    } catch (err) {
      console.error("Microphone error:", err);
      alert("Enable microphone access.");
    }
  });

  // ⏹ Stop early
  stopButton.addEventListener("click", () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      status.textContent    = "Processing…";
      stopButton.disabled   = true;
      recordButton.disabled = false;
    }
  });

  // 🔄 Upload & display results in chat
  async function sendAudio(blob) {
    const form = new FormData();
    form.append("file", blob, "recording.wav");

    try {
      const res = await fetch("/predict", {
        method: "POST",
        body: form,
        headers: { "Accept": "application/json" }
      });
      if (!res.ok) throw new Error(await res.text());

      const data = await res.json();
      if (!data.probabilities) throw new Error("No probabilities returned");

      // 1) Build the probability sentence
      const parts = Object.entries(data.probabilities)
        .map(([emo, pct]) => `${emo}: ${pct}%`);
      const sentence = `You’re feeling: ${parts.join(", ")}`;

      // 2) Initialize chat history with sentence + blank line + initial reply
      chatHistoryEl.innerHTML = `
        <div class="assistant">📝 ${sentence}</div>
        <br>
        <div class="assistant">🤖 ${data.reply}</div>
      `;

      // 3) Reveal chat UI
      chatId = data.chat_id;
      chatDiv.classList.remove("hidden");
      status.textContent = "✅ Done!";

    } catch (err) {
      console.error("Upload error:", err);
      alert("Failed to detect emotion.");
      status.textContent = "⚠️ Error";
    }
  }

  // 📨 Send chat messages
  sendBtn.addEventListener("click", async () => {
    const text = userMessage.value.trim();
    if (!text || !chatId) return;

    // Append user message
    chatHistoryEl.innerHTML += `<div class="user">🧑 ${text}</div>`;
    userMessage.value = "";

    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, message: text })
      });
      const { reply, error } = await res.json();
      if (error) throw new Error(error);

      // Append assistant reply
      chatHistoryEl.innerHTML += `<div class="assistant">🤖 ${reply}</div>`;
      chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;

    } catch (err) {
      console.error("Chat error:", err);
      alert("Failed to send message.");
    }
  });
});





// window.addEventListener("DOMContentLoaded", () => {
//   let audioChunks = [];
//   let mediaRecorder;
//   let chatId = null;

//   const recordButton  = document.getElementById("recordBtn");
//   const stopButton    = document.getElementById("stopBtn");
//   const status        = document.getElementById("status");

//   // Chat UI elements
//   const chatDiv       = document.getElementById("chat");
//   const chatHistoryEl = document.getElementById("chatHistory");
//   const userMessage   = document.getElementById("userMessage");
//   const sendBtn       = document.getElementById("sendBtn");

//   // 🎤 Start Recording
//   recordButton.addEventListener("click", async () => {
//     try {
//       const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
//       mediaRecorder = new MediaRecorder(stream);
//       audioChunks = [];

//       mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
//       mediaRecorder.onstop = async () => {
//         status.textContent = "Uploading…";
//         await sendAudio(new Blob(audioChunks, { type: "audio/wav" }));
//       };

//       mediaRecorder.start();
//       status.textContent    = "🎙️ Recording…";
//       recordButton.disabled = true;
//       stopButton.disabled   = false;

//       // Auto‑stop after 5s
//       setTimeout(() => {
//         if (mediaRecorder.state === "recording") {
//           mediaRecorder.stop();
//           stopButton.disabled   = true;
//           recordButton.disabled = false;
//         }
//       }, 5000);

//     } catch (err) {
//       console.error("Microphone error:", err);
//       alert("Enable microphone access.");
//     }
//   });

//   // ⏹ Stop early
//   stopButton.addEventListener("click", () => {
//     if (mediaRecorder && mediaRecorder.state === "recording") {
//       mediaRecorder.stop();
//       status.textContent    = "Processing…";
//       stopButton.disabled   = true;
//       recordButton.disabled = false;
//     }
//   });

//   // 🔄 Upload & display results in chat
//   async function sendAudio(blob) {
//     const form = new FormData();
//     form.append("file", blob, "recording.wav");

//     try {
//       const res = await fetch("/predict", {
//         method: "POST",
//         body: form,
//         headers: { "Accept": "application/json" }
//       });
//       if (!res.ok) throw new Error(await res.text());

//       const data = await res.json();
//       if (!data.probabilities) throw new Error("No probabilities returned");

//       // 1) Build the probability sentence
//       const parts = Object.entries(data.probabilities)
//         .map(([emo, pct]) => `${emo}: ${pct}%`);
//       const sentence = `You’re feeling: ${parts.join(", ")}`;

//       // 2) Initialize chat history with sentence + initial reply
//       chatHistoryEl.innerHTML = `
//         <div class="assistant">📝 ${sentence}</div>
//         <div class="assistant">🤖 ${data.reply}</div>
//       `;

//       // 3) Reveal chat UI
//       chatId = data.chat_id;
//       chatDiv.classList.remove("hidden");
//       status.textContent = "✅ Done!";

//     } catch (err) {
//       console.error("Upload error:", err);
//       alert("Failed to detect emotion.");
//       status.textContent = "⚠️ Error";
//     }
//   }

//   // 📨 Send chat messages
//   sendBtn.addEventListener("click", async () => {
//     const text = userMessage.value.trim();
//     if (!text || !chatId) return;

//     // Append user message
//     chatHistoryEl.innerHTML += `<div class="user">🧑 ${text}</div>`;
//     userMessage.value = "";

//     try {
//       const res = await fetch("/chat", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ chat_id: chatId, message: text })
//       });
//       const { reply, error } = await res.json();
//       if (error) throw new Error(error);

//       // Append assistant reply
//       chatHistoryEl.innerHTML += `<div class="assistant">🤖 ${reply}</div>`;
//       chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;

//     } catch (err) {
//       console.error("Chat error:", err);
//       alert("Failed to send message.");
//     }
//   });
// });





