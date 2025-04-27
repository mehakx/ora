# Final app.py

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
UPLOADCARE_PUB_KEY = os.getenv("UPLOADCARE_PUB_KEY")

conversations = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/uploadcare-proxy", methods=["POST"])
def uploadcare_proxy():
    try:
        print(f"DEBUG: Uploadcare Public Key being used → {UPLOADCARE_PUB_KEY}")

        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files['file']
        file_content = file.read()
        file_size = len(file_content)

        init_response = requests.post(
            f"https://upload.uploadcare.com/multipart/start/?pub_key={UPLOADCARE_PUB_KEY}",
            json={
                "filename": file.filename,
                "size": file_size,
                "content_type": file.content_type
            },
            headers={
                "Content-Type": "application/json"
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

        upload_response = requests.put(
            upload_url,
            data=file_content,
            headers={'Content-Type': 'application/octet-stream'}
        )
        print(f"Part upload response: {upload_response.status_code}")

        if upload_response.status_code != 200:
            return jsonify({"error": f"Failed to upload file part: {upload_response.text}"}), 500

        complete_response = requests.post(
            "https://upload.uploadcare.com/multipart/complete/",
            json={
                "uuid": uuid_value,
                "pub_key": UPLOADCARE_PUB_KEY
            },
            headers={
                "Content-Type": "application/json"
            }
        )
        print(f"Complete upload response: {complete_response.text}")

        if complete_response.status_code != 200:
            return jsonify({"error": f"Failed to complete upload: {complete_response.text}"}), 500

        return jsonify({"file": uuid_value}), 200

    except Exception as e:
        print("❌ Uploadcare Proxy Error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# (predict and chat routes unchanged)

if __name__ == "__main__":
    app.run(debug=True)
