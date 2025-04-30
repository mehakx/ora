// Get our elements
const recordBtn    = document.getElementById('recordBtn');
const stopBtn      = document.getElementById('stopBtn');
const statusEl     = document.getElementById('status');
const resultDiv    = document.getElementById('result');
const emotionLabel = document.getElementById('emotionLabel');
const replyLabel   = document.getElementById('replyLabel');

// Set up Web Speech API
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SpeechRecognition) {
  statusEl.textContent = '⚠️ Your browser does not support SpeechRecognition.';
  recordBtn.disabled = true;
}

const recognition = new SpeechRecognition();
recognition.lang = 'en-US';
recognition.interimResults = false;
recognition.maxAlternatives = 1;

// When you click “Record”
recordBtn.addEventListener('click', () => {
  // Reset UI
  statusEl.textContent = 'Listening…';
  resultDiv.classList.add('hidden');
  emotionLabel.textContent = '—';
  replyLabel.textContent   = '—';

  // Toggle buttons
  recordBtn.disabled = true;
  stopBtn.disabled   = false;

  // Start listening
  recognition.start();
});

// When you click “Stop”
stopBtn.addEventListener('click', () => {
  recognition.stop();
});

// When the speech recognition returns a transcript
recognition.addEventListener('result', async (e) => {
  const transcript = e.results[0][0].transcript;
  statusEl.textContent = `You said: “${transcript}”\nAnalyzing emotion…`;

  // Immediately disable stop button
  stopBtn.disabled = true;

  try {
    // Send to your /analyze endpoint
    const resp = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: transcript })
    });

    const { emotion, message } = await resp.json();

    // Populate and reveal result
    emotionLabel.textContent = emotion;
    replyLabel.textContent   = message;
    resultDiv.classList.remove('hidden');

  } catch (err) {
    console.error(err);
    statusEl.textContent = '⚠️ Error analyzing emotion.';
  } finally {
    // Re-enable record button
    recordBtn.disabled = false;
    statusEl.textContent += '\n— done —';
  }
});

// Handle any speech errors
recognition.addEventListener('error', (e) => {
  statusEl.textContent = `⚠️ Speech error: ${e.error}`;
  recordBtn.disabled = false;
  stopBtn.disabled   = true;
});


