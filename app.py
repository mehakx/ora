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

# Allow CORS
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:5173",
    "http://localhost:5500",
    "https://your-netlify-site.netlify.app",
    "https://ora-owjy.onrender.com"
]}})

HUME_API_KEY = os.getenv("HUME_API_KEY")
UPLOADCARE_PUB_KEY = os.getenv("UPLOADCARE_PUB_KEY")

# DEBUG: Print keys to confirm they are loaded
print(f"🔑 Loaded Uploadcare key: {UPLOADCARE_PUB_KEY}")
print(f"🔑 Loaded Hume key: {HUME_API_KEY}")

# In-memory conversation storage
conversations = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/uploadcare-proxy", methods=["POST"])
def uploadcare_proxy():
    try:
        if not UPLOADCARE_PUB_KEY:
            print("❌ ERROR: UPLOADCARE_PUB_KEY is not loaded properly!")
            return jsonify({"error": "Server misconfiguration: Uploadcare public key missing."}), 500
        
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        file_content = file.read()
        file_size = len(file_content)

        print(f"📦 Received file: {file.filename} | Size: {file_size}")

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
        print(f"Multipart init response: {init_response.status_code} {init_response.text}")

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
        print(f"Complete upload response: {complete_response.status_code} {complete_response.text}")

        if complete_response.status_code != 200:
            return jsonify({"error": f"Failed to complete upload: {complete_response.text}"}), 500

        return jsonify({"file": uuid_value}), 200

    except Exception as e:
        print("❌ Uploadcare Proxy Error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Predict and Chat routes (unchanged, you already had these)

if __name__ == "__main__":
    app.run(debug=True)
