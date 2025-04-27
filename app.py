import os
import uuid
import traceback
import requests
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from dotenv import load_dotenv
import time

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
        data = request.get_json()
        audio_url = data.get("audio_url")

        if not audio_url:
            return jsonify({"error": "Missing audio URL"}), 400

        # Create Batch Job
        payload = {
            "urls": [audio_url],
            "models": {"prosody": {}}
        }

        headers = {
            "X-Hume-Api-Key": HUME_API_KEY,
            "Content-Type": "application/json"
        }

        print("✅ Creating Batch Job...")
        response = requests.post(
            "https://api.hume.ai/v0/batch/jobs",
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            print(f"❌ Failed to create job: {response.text}")
            return jsonify({"error": "Hume API job creation failed"}), 500

        job_data = response.json()
        job_id = job_data.get("job_id")

        if not job_id:
            return jsonify({"error": "No job_id returned from Hume"}), 500

        # Poll for job completion
        print(f"⏳ Polling for job {job_id}...")
        status = "running"
        while status != "done":
            time.sleep(3)
            status_response = requests.get(
                f"https://api.hume.ai/v0/batch/jobs/{job_id}",
                headers=headers
            )
            status_data = status_response.json()
            status = status_data.get("status")
            print(f"Polling... Current status: {status}")

        # When done, get predictions
        predictions = status_data.get("predictions", [])

        if not predictions:
            return jsonify({"error": "No predictions found"}), 500

        emotions = predictions[0]["models"]["prosody"]["grouped_predictions"][0]["predictions"][0]["emotions"]
        top_emotion = max(emotions, key=lambda emo: emo["score"])
        emotion_probs = {emo["name"]: round(emo["score"] * 100, 1) for emo in emotions}

        reply = f"I'm here for you. It sounds like you're feeling {top_emotion['name']}."

        chat_id = uuid.uuid4().hex
        conversations[chat_id] = [
            {"role": "system",    "content": "You are a compassionate assistant."},
            {"role": "user",      "content": f"I am feeling {top_emotion['name']}."},
            {"role": "assistant", "content": reply}
        ]

        return jsonify({
            "emotion": top_emotion["name"],
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

        assistant_msg = f"I hear you. Thanks for sharing."

        conversations[chat_id].append({"role": "assistant", "content": assistant_msg})

        return jsonify({"reply": assistant_msg})

    except Exception as e:
        print("❌ Chat error:")
        traceback.print_exc()
        return jsonify({"error": "Something went wrong during chat."}), 500
