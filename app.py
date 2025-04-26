import os
import uuid
import traceback
import io
import requests
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from pydub import AudioSegment
from dotenv import load_dotenv

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
        audio_seg = AudioSegment.from_file(io.BytesIO(blob))
        audio_seg = audio_seg.set_frame_rate(44100).set_channels(1)
        audio_seg = audio_seg[:5000]  # Limit audio to 5 seconds

        temp_filename = "temp_audio.wav"
        audio_seg.export(temp_filename, format="wav")

        with open(temp_filename, "rb") as f:
            files = {
                "file": ("temp_audio.wav", f, "audio/wav")
            }
            headers = {
                "Authorization": f"Bearer {HUME_API_KEY}"
            }
            response = requests.post(
                "https://api.hume.ai/v0/voice",
                files=files,
                headers=headers
            )

        if response.status_code != 200:
            print(f"❌ Hume API Error: {response.text}")
            return jsonify({"error": "Hume API request failed"}), 500

        data = response.json()
        emotions = data.get("predictions", [{}])[0].get("emotions", {})

        if not emotions:
            return jsonify({"error": "No emotions found"}), 500

        top_emotion = max(emotions, key=lambda k: emotions[k])
        emotion_probs = {emo: round(prob * 100, 1) for emo, prob in emotions.items()}

        reply = f"I'm here for you. It sounds like you're feeling {top_emotion}."

        chat_id = uuid.uuid4().hex
        conversations[chat_id] = [
            {"role": "system",    "content": "You are a compassionate assistant."},
            {"role": "user",      "content": f"I am feeling {top_emotion}."},
            {"role": "assistant", "content": reply}
        ]

        return jsonify({
            "emotion": top_emotion,
            "probabilities": emotion_probs,
            "reply": reply,
            "chat_id": chat_id
        })

    except Exception as e:
        print("❌ Prediction error:")
        traceback.print_exc()
        return jsonify({"error": "Something went wrong processing your file."}), 500

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

        # Since OpenAI call is removed, we can just echo a basic assistant response
        assistant_msg = f"I hear you. Thanks for sharing."

        conversations[chat_id].append({"role": "assistant", "content": assistant_msg})

        return jsonify({"reply": assistant_msg})

    except Exception as e:
        print("❌ Chat error:")
        traceback.print_exc()
        return jsonify({"error": "Something went wrong during chat."}), 500



























