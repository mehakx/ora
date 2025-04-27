import os
import uuid
import time
import traceback
import requests
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "supersecret")

# Allow CORS from both localhost and production
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:5173",
    "http://localhost:5500",
    "https://your-netlify-site.netlify.app",
    "https://ora-owjy.onrender.com"
]}})

HUME_API_KEY = os.getenv("HUME_API_KEY")
UPLOADCARE_PUB_KEY = os.getenv("UPLOADCARE_PUB_KEY")

# Simple in-memory conversation store
conversations = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/uploadcare-proxy", methods=["POST"])
def uploadcare_proxy():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files['file']
        file_content = file.read()
        file_size = len(file_content)

        # Step 1: Initialize multipart upload
        init_response = requests.post(
            'https://upload.uploadcare.com/multipart/start/',
            json={
                "filename": file.filename,
                "size": file_size,
                "content_type": file.content_type,
                "pub_key": UPLOADCARE_PUB_KEY
            }
        )

        print(f"Multipart init response: {init_response.text}")

        if init_response.status_code != 200:
            return jsonify({"error": f"Failed to initialize upload: {init_response.text}"}), 500

        init_data = init_response.json()
        upload_url = init_data.get('parts_urls', [])[0]
        uuid_value = init_data.get('uuid')

        if not upload_url or not uuid_value:
            return jsonify({"error": "Missing upload URL or UUID from Uploadcare"}), 500

        # Step 2: Upload part
        upload_response = requests.put(
            upload_url,
            data=file_content,
            headers={'Content-Type': 'application/octet-stream'}
        )

        print(f"Part upload response: {upload_response.status_code}")

        if upload_response.status_code != 200:
            return jsonify({"error": f"Failed to upload file part: {upload_response.text}"}), 500

        # Step 3: Complete multipart upload
        complete_response = requests.post(
            'https://upload.uploadcare.com/multipart/complete/',
            json={
                "uuid": uuid_value,
                "pub_key": UPLOADCARE_PUB_KEY
            }
        )

        print(f"Complete upload response: {complete_response.text}")

        if complete_response.status_code != 200:
            return jsonify({"error": f"Failed to complete upload: {complete_response.text}"}), 500

        return jsonify({"file": uuid_value}), 200

    except Exception as e:
        print("\u274c Uploadcare Proxy Error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()
        print("\u2705 Received data:", data)

        if not data or "audio_url" not in data:
            return jsonify({"error": "No audio URL received"}), 400

        audio_url = data["audio_url"]
        print("\u2705 Received audio URL:", audio_url)

        # Step 2: Create a Hume Batch job
        payload = {
            "urls": [audio_url],
            "models": {"prosody": {}}
        }
        headers = {
            "X-Hume-Api-Key": HUME_API_KEY,
            "Content-Type": "application/json"
        }

        print("\u2705 Submitting batch job...")
        response = requests.post("https://api.hume.ai/v0/batch/jobs", headers=headers, json=payload)

        if response.status_code != 200:
            print(f"\u274c Failed to create Hume job: {response.text}")
            return jsonify({"error": "Failed to create Hume job"}), 500

        job_data = response.json()
        job_id = job_data.get("job_id")

        if not job_id:
            return jsonify({"error": "No job_id returned from Hume API"}), 500

        print(f"\u23f3 Polling Hume job ID {job_id}...")

        # Step 3: Poll until job is done
        while True:
            time.sleep(3)
            status_response = requests.get(f"https://api.hume.ai/v0/batch/jobs/{job_id}", headers=headers)
            status_data = status_response.json()
            job_status = status_data.get("status")

            print(f"\ud83d\udd04 Job status: {job_status}")
            if job_status == "done":
                break

        # Step 4: Process emotion predictions
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
        print("\u274c Prediction error:", e)
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
        print("\u274c Chat error:", e)
        traceback.print_exc()
        return jsonify({"error": "Something went wrong during chat."}), 500

if __name__ == "__main__":
    app.run(debug=True)
