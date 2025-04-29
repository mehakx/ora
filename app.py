# Final working app.py with improved error handling

import os
import uuid
import time
import traceback
import requests
from flask import Flask, request, jsonify, render_template, url_for
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

# Create upload directory at startup - with better error handling
UPLOAD_FOLDER = os.path.join("static", "uploads")
print(f"⚙️ Current working directory: {os.getcwd()}")
print(f"⚙️ Attempting to set up upload folder: {UPLOAD_FOLDER}")

try:
    if not os.path.exists("static"):
        print("📁 Creating static directory")
        os.makedirs("static")
    
    if os.path.isfile(UPLOAD_FOLDER):
        print(f"🔄 Removing file at {UPLOAD_FOLDER} to create directory")
        os.remove(UPLOAD_FOLDER)
    
    if not os.path.exists(UPLOAD_FOLDER):
        print(f"📁 Creating uploads directory: {UPLOAD_FOLDER}")
        os.makedirs(UPLOAD_FOLDER)
        
    print(f"✅ Upload directory ready: {UPLOAD_FOLDER}")
except Exception as e:
    print(f"⚠️ Warning: Could not prepare upload directory: {str(e)}")
    traceback.print_exc()

conversations = {}

@app.route("/")
def index():
    return render_template("index.html")

# Fixed Upload Route with better error handling
@app.route("/upload", methods=["POST"])
def upload_audio():
    try:
        print("⚙️ Processing upload request")
        if 'file' not in request.files:
            print("❌ No file in request")
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files['file']
        print(f"✅ Received file: {file.filename}")
        
        filename = uuid.uuid4().hex + ".webm"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        print(f"⚙️ Attempting to save file to: {file_path}")
        
        # Ensure directory exists before saving
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        file.save(file_path)
        print(f"✅ File saved successfully: {file_path}")
        
        # Create a fully qualified URL
        host = request.host_url.rstrip('/')
        public_url = f"{host}/static/uploads/{filename}"
        print(f"🔗 File URL: {public_url}")
        
        return jsonify({"audio_url": public_url}), 200

    except Exception as e:
        print(f"❌ Upload Error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()
        print("⚙️ Predict request data:", data)

        if not data or "audio_url" not in data:
            print("❌ No audio URL in request")
            return jsonify({"error": "No audio URL received"}), 400

        audio_url = data["audio_url"]
        print(f"🔗 Processing audio URL: {audio_url}")

        payload = {
            "urls": [audio_url],
            "models": {"prosody": {}}
        }
        headers = {
            "X-Hume-Api-Key": HUME_API_KEY,
            "Content-Type": "application/json"
        }

        print("⚙️ Submitting batch job to Hume...")
        response = requests.post("https://api.hume.ai/v0/batch/jobs", headers=headers, json=payload)
        
        print(f"⚙️ Hume API response: {response.status_code}")
        print(f"⚙️ Hume API body: {response.text[:200]}...")  # Print first 200 chars

        if response.status_code != 200:
            print(f"❌ Failed to create Hume job: {response.text}")
            return jsonify({"error": f"Failed to create Hume job: {response.text}"}), 500

        job_data = response.json()
        job_id = job_data.get("job_id")

        if not job_id:
            print("❌ No job_id in Hume response")
            return jsonify({"error": "No job_id returned from Hume API"}), 500

        print(f"⏳ Polling Hume job ID {job_id}...")

        max_attempts = 20
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            time.sleep(3)
            status_response = requests.get(f"https://api.hume.ai/v0/batch/jobs/{job_id}", headers=headers)
            status_data = status_response.json()
            job_status = status_data.get("status")

            print(f"🔄 Job status ({attempt}/{max_attempts}): {job_status}")
            if job_status == "done":
                break
                
        if job_status != "done":
            print("❌ Hume job timed out")
            return jsonify({"error": "Hume processing timed out"}), 500

        predictions = status_data.get("predictions", [])
        if not predictions:
            print("❌ No predictions in Hume response")
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
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

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
        return jsonify({"error": f"Chat error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
