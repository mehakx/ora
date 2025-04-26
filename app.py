import os
import uuid
import traceback
import io
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from pydub import AudioSegment
from dotenv import load_dotenv
from hume import HumeClient

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "supersecret")
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:5173",
    "https://your-netlify-site.netlify.app"
]}})

HUME_API_KEY = os.getenv("HUME_API_KEY")

# In-memory chat store
conversations = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        blob = request.files["file"].read()

        # Process audio
        audio_seg = AudioSegment.from_file(io.BytesIO(blob))
        audio_seg = audio_seg.set_frame_rate(44100).set_channels(1)
        audio_seg = audio_seg[:5000]  # Limit to 5 seconds
        
        # Export to WAV format
        wav_io = io.BytesIO()
        audio_seg.export(wav_io, format="wav")
        wav_io.seek(0)
        
        # Save temporarily to a file if needed by the Hume client
        temp_path = "/tmp/audio_temp.wav"
        with open(temp_path, "wb") as f:
            f.write(wav_io.getvalue())
        
        # Initialize Hume client
        client = HumeClient(api_key=HUME_API_KEY)
        
        # Submit job using file path
        job = client.empathic_voice.batch.submit_job(files=[temp_path])
        job_result = job.await_complete()
        
        # Clean up temp file
        os.remove(temp_path)
        
        # Parse emotions
        predictions = job_result.get("models", {}).get("prosody", {}).get("grouped_predictions", [])
        if not predictions or not predictions[0].get("predictions"):
            return jsonify({"error": "No predictions found in response"}), 500
            
        raw_emotions = predictions[0]["predictions"][0].get("emotions", [])
        emotions = {emo["name"]: emo["score"] for emo in raw_emotions}
        
        if not emotions:
            return jsonify({"error": "No emotions found"}), 500
            
        top_emotion = max(emotions, key=lambda k: emotions[k])
        emotion_probs = {emo: round(prob * 100, 1) for emo, prob in emotions.items()}
        
        reply = f"I'm here for you. It sounds like you're feeling {top_emotion}."
        
        chat_id = uuid.uuid4().hex
        conversations[chat_id] = [
            {"role": "system", "content": "You are a compassionate assistant."},
            {"role": "user", "content": f"I am feeling {top_emotion}."},
            {"role": "assistant", "content": reply}
        ]
        
        return jsonify({
            "emotion": top_emotion,
            "probabilities": emotion_probs,
            "reply": reply,
            "chat_id": chat_id
        })
        
    except Exception as e:
        print("❌ Prediction error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        chat_id = data.get("chat_id")
        user_msg = data.get("message", "").strip()
        
        if not chat_id or chat_id not in conversations:
            return jsonify({"error": "Invalid or missing chat_id"}), 400
        if not user_msg:
            return jsonify({"error": "Empty message"}), 400
            
        conversations[chat_id].append({"role": "user", "content": user_msg})
        
        assistant_msg = f"I hear you. Thanks for sharing."
        conversations[chat_id].append({"role": "assistant", "content": assistant_msg})
        
        return jsonify({"reply": assistant_msg})
        
    except Exception as e:
        print("❌ Chat error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
