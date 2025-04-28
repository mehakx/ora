# FINAL app.py (Direct Server Upload)

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

# Allow CORS for local dev + production
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:5173",
    "http://localhost:5500",
    "https://your-netlify-site.netlify.app",
    "https://ora-owjy.onrender.com"
]}})

# Folder where uploaded files will be saved
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HUME_API_KEY = os.getenv("HUME_API_KEY")

conversations = {}

@app.route("/")
def index():
    return render_template("index.html")

# ✅ New Upload Route
@app.route("/upload", methods=["POST"])
def upload_audio():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        filename = f"{uuid.uuid4().hex}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        file_url = f"https://{request.host}/uploads/{filename}"

        print(f"✅ Uploaded file accessible at: {file_url}")

        return jsonify({"url": file_url}), 200

    except Exception as e:
        print("\u274c Upload error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ✅ Serve Uploaded Files
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# (Your /predict and /chat routes stay SAME)

if __name__ == "__main__":
    app.run(debug=True)
