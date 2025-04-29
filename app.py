import os
import uuid
import time
import traceback
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "supersecret")

# Allow CORS from your front-end origins
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:5173",
    "http://localhost:5500",
    "https://your-netlify-site.netlify.app",
    "https://ora-owjy.onrender.com"
]}})

# Your Hume API key
HUME_API_KEY = os.getenv("HUME_API_KEY")

# Simple in-memory conversation store
conversations = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze-audio", methods=["POST"])
def analyze_audio():
    try:
        # 1) Make sure a file was sent
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file in request"}), 400
            
        audio_file = request.files['audio']
        audio_content = audio_file.read()
        
        # 2) Forward to Hume API - Using batch jobs endpoint
        print("✅ Forwarding audio to Hume...")
        
        # Create a multipart form for uploading the audio file
        files = {
            'file': (audio_file.filename, audio_content, audio_file.content_type)
        }
        
        # Try the batch jobs endpoint with file upload
        hume_resp = requests.post(
            "https://api.hume.ai/v0/batch/jobs",
            headers={"X-Hume-Api-Key": HUME_API_KEY},
            files=files,
            data={"models": '{"prosody": {}}'}  # JSON as string
        )
        
        if not hume_resp.ok:
            error_text = hume_resp.text
            print(f"❌ Hume API error: {hume_resp.status_code} - {error_text}")
            return jsonify({"error": f"Hume API error: {hume_resp.status_code} - {error_text}"}), hume_resp.status_code
        
        # Get job ID and poll until complete
        job_data = hume_resp.json()
        print(f"✅ Hume job created: {job_data}")
        
        job_id = job_data.get("job_id")
        if not job_id:
            return jsonify({"error": "No job ID returned from Hume"}), 500
        
        # Poll for results
        print(f"✅ Polling Hume job ID: {job_id}")
        
        max_attempts = 15
        for attempt in range(max_attempts):
            print(f"Polling attempt {attempt+1}/{max_attempts}")
            time.sleep(2)  # Wait between polls
            
            status_resp = requests.get(
                f"https://api.hume.ai/v0/batch/jobs/{job_id}",
                headers={"X-Hume-Api-Key": HUME_API_KEY}
            )
            
            if not status_resp.ok:
                print(f"Poll error: {status_resp.status_code} - {status_resp.text}")
                continue
                
            status_data = status_resp.json()
            print(f"Poll status: {status_data.get('status')}")
            
            if status_data.get("status") == "done":
                # Process results
                predictions = status_data.get("predictions", [])
                if not predictions:
                    return jsonify({"error": "No predictions in Hume response"}), 500
                
                # Extract emotions from the response
                try:
                    emotions = predictions[0]["models"]["prosody"]["grouped_predictions"][0]["predictions"][0]["emotions"]
                    
                    # Build probabilities and determine top emotion
                    probs = {e["name"]: round(e["score"] * 100, 1) for e in emotions}
                    top = max(emotions, key=lambda e: e["score"])["name"]
                    reply = f"I'm here for you. It sounds like you're feeling {top}."
                    
                    # 4) Start a new chat session
                    chat_id = uuid.uuid4().hex
                    conversations[chat_id] = [
                        {"role": "system", "content": "You are a compassionate assistant."},
                        {"role": "user", "content": f"I am feeling {top}."},
                        {"role": "assistant", "content": reply}
                    ]
                    
                    return jsonify({
                        "emotion": top,
                        "probabilities": probs,
                        "reply": reply,
                        "chat_id": chat_id
                    })
                except (KeyError, IndexError) as e:
                    print(f"❌ Error parsing Hume response: {e}")
                    print(f"Response structure: {status_data}")
                    return jsonify({"error": f"Error parsing Hume response: {e}"}), 500
        
        return jsonify({"error": "Hume analysis timed out"}), 504
        
    except Exception as e:
        print("❌ Analysis error:", e)
        traceback.print_exc()
        return jsonify({"error": "Analysis failed: " + str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        chat_id = data.get("chat_id")
        user_msg = data.get("message", "").strip()
        
        if not chat_id or chat_id not in conversations:
            return jsonify({"error": "Invalid or missing chat_id"}), 400
        if not user_msg:
            return jsonify({"error": "Empty message"}), 400
            
        # Append user message
        conversations[chat_id].append({"role": "user", "content": user_msg})
        assistant_msg = "I hear you. Thanks for sharing."
        conversations[chat_id].append({"role": "assistant", "content": assistant_msg})
        
        return jsonify({"reply": assistant_msg})
        
    except Exception as e:
        print("❌ Chat error:", e)
        traceback.print_exc()
        return jsonify({"error": "Chat failed: " + str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
