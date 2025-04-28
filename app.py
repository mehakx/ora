# FINAL app.py (Direct Server Upload)

# Final working app.py (direct server upload to /static/uploads)

import os
import uuid
import time
import traceback
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "supersecret")

# CORS settings
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:5173",
    "http://localhost:5500",
    "https://your-netlify-site.netlify.app",
    "https://ora-owjy.onrender.com"
]}})

# Make sure the uploads folder exists
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HUME_API_KEY = os.getenv("HUME_API_KEY")

conversations = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_to_server():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files['file']
        filename = uuid.uuid4().hex + ".webm"
        save_path = os.path.join(UPLOAD_FOLDER, filename)

        file.save(save_path)

        file_url = f"/static/uploads/{filename}"
        print(f"✅ File uploaded and saved: {file_url}")

        return jsonify({"file_url": file_url}), 200

    except Exception as e:
        print("❌ Upload to server error:", e)
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
        full_audio_url = f"https://ora-owjy.onrender.com{audio_url}"
        print("✅ Full audio URL:", full_audio_url)

        payload = {
            "urls": [full_audio_url],
            "models": {"prosody": {}}
        }
        headers = {
            "X-Hume-Api-Key": HUME_API_KEY,
            "Content-Type": "application/json"
        }

        print("✅ Submitting to Hume API...")
        response = requests.post("https://api.hume.ai/v0/batch/jobs", headers=headers, json=payload)

        if response.status_code != 200:
            print(f"❌ Failed to create Hume job: {response.text}")
            return jsonify({"error": "Failed to create Hume job"}), 500

        job_data = response.json()
        job_id = job_data.get("job_id")

        if not job_id:
            return jsonify({"error": "No job_id returned"}), 500

        print(f"⏳ Polling Hume job {job_id}...")

        while True:
            time.sleep(3)
            status_response = requests.get(f"https://api.hume.ai/v0/batch/jobs/{job_id}", headers=headers)
            status_data = status_response.json()
            if status_data.get("status") == "done":
                break

        predictions = status_data.get("predictions", [])
        if not predictions:
            return jsonify({"error": "No predictions"}), 500

        emotions = predictions[0]["models"]["prosody"]["grouped_predictions"][0]["predictions"][0]["emotions"]
        top_emotion = max(emotions, key=lambda emo: emo["score"])
        emotion_probs = {emo["name"]: round(emo["score"] * 100, 1) for emo in emotions}

        reply = f"I'm here for you. It sounds like you're feeling {top_emotion['name']}."

        chat_id = uuid.uuid4().hex
        conversations[chat_id] = [
            {"role": "system", "content": "You are a compassionate assistant."},
            {"role": "user", "content": f"I am feeling {top_emotion['name']}."},
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
        return jsonify({"error": "Something went wrong during prediction."}), 500

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        chat_id = data.get("chat_id")
        user_msg = data.get("message", "").strip()

        if not chat_id or chat_id not in conversations:
            return jsonify({"error": "Invalid chat_id"}), 400
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
