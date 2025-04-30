const recordBtn = document.getElementById('record');
const stopBtn   = document.getElementById('stop');
const statusEl = document.getElementById('status');
const resultEl = document.getElementById('result');

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SpeechRecognition) {
  statusEl.textContent = '⚠️ Your browser does not support SpeechRecognition.';
  recordBtn.disabled = true;
}

const recognition = new SpeechRecognition();
recognition.lang = 'en-US';
recognition.interimResults = false;
recognition.maxAlternatives = 1;

recordBtn.addEventListener('click', () => {
  resultEl.textContent = '';
  statusEl.textContent = 'Listening…';
  recordBtn.disabled = true;
  stopBtn.disabled = false;
  recognition.start();
});

stopBtn.addEventListener('click', () => {
  recognition.stop();
});

recognition.addEventListener('result', async (e) => {
  const transcript = e.results[0][0].transcript;
  statusEl.textContent = `You said: “${transcript}”`;
  stopBtn.disabled = true;
  statusEl.textContent += '\nAnalyzing emotion…';

  try {
    const resp = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: transcript })
    });
    const { emotion, message } = await resp.json();
    resultEl.innerHTML = `<strong>Emotion:</strong> ${emotion}<br/><strong>Response:</strong> ${message}`;
  } catch (err) {
    resultEl.textContent = '⚠️ Error analyzing emotion.';
    console.error(err);
  } finally {
    statusEl.textContent = '— done —';
    recordBtn.disabled = false;
  }
});

recognition.addEventListener('error', (e) => {
  statusEl.textContent = `⚠️ Speech error: ${e.error}`;
  recordBtn.disabled = false;
  stopBtn.disabled = true;
});

