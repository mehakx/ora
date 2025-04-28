# Final working app.py with local upload route

import os
import uuid
import time
import traceback
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "supersecret")

CORS(app, resources={r"/*": {"origins": [
    "http://localhost:5173",
    "http://localhost:5500",
    "https://your-netlify-site.netlify.app",
    "https://ora-owjy.onrender.com"
]}})

HUME_API_KEY = os.getenv("HUME_API_KEY")

conversations = {}

@app.route("/")
def index():
    return render_template("index.html")

# New Upload Route
@app.route("/upload", methods=["POST"])
def upload_audio():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files['file']
        filename = uuid.uuid4().hex + ".webm"
        upload_folder = os.path.join("static", "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        public_url = f"/static/uploads/{filename}"
        return jsonify({"url": public_url}), 200

    except Exception as e:
        print("\u274c Upload Error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()
        print("✅ Received data:", data)

        if not data or "audio_url" not in data:
            return jsonify({"error": "No audio URL received"}), 400

        audio_url = data["audio_url"]
        print("✅ Received audio URL:", audio_url)

        payload = {
            "urls": [audio_url],
            "models": {"prosody": {}}
        }
        headers = {
            "X-Hume-Api-Key": HUME_API_KEY,
            "Content-Type": "application/json"
        }

        print("✅ Submitting batch job...")
        response = requests.post("https://api.hume.ai/v0/batch/jobs", headers=headers, json=payload)

        if response.status_code != 200:
            print(f"❌ Failed to create Hume job: {response.text}")
            return jsonify({"error": "Failed to create Hume job"}), 500

        job_data = response.json()
        job_id = job_data.get("job_id")

        if not job_id:
            return jsonify({"error": "No job_id returned from Hume API"}), 500

        print(f"⏳ Polling Hume job ID {job_id}...")

        while True:
            time.sleep(3)
            status_response = requests.get(f"https://api.hume.ai/v0/batch/jobs/{job_id}", headers=headers)
            status_data = status_response.json()
            job_status = status_data.get("status")

            print(f"🔄 Job status: {job_status}")
            if job_status == "done":
                break

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
        print("❌ Prediction error:", e)
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

        assistant_msg = "I hear you. Thanks for sharing."
        conversations[chat_id].append({"role": "assistant", "content": assistant_msg})

        return jsonify({"reply": assistant_msg})

    except Exception as e:
        print("❌ Chat error:", e)
        traceback.print_exc()
        return jsonify({"error": "Something went wrong during chat."}), 500

if __name__ == "__main__":
    app.run(debug=True)
