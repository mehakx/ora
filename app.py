import os
import uuid
import pickle
import traceback
import io
import numpy as np
import openai
from dotenv import load_dotenv

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from pydub import AudioSegment
from prototype import extract_feature
from sklearn.preprocessing import StandardScaler

# Load env & set OpenAI key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Flask
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "supersecret")
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:5173",
    "https://your-netlify-site.netlify.app"
]}})

# Load your trained model & label encoder
with open("trained_emotion_model.pkl", "rb") as f:
    model = pickle.load(f)
with open("label_encoder.pkl", "rb") as f:
    encoder = pickle.load(f)

# In‑memory store of conversations: chat_id → message list
conversations = {}

@app.route("/")
def index():
    return render_template("index.html")

def generate_initial_reply(emotion: str) -> str:
    """First reply based on detected emotion."""
    system = {
        "role": "system",
        "content": "You are a compassionate assistant who responds empathetically to user emotions."
    }
    user = {
        "role": "user",
        "content": f"I am feeling {emotion}. How would you respond?"
    }
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[system, user],
        max_tokens=100,
    )
    return resp.choices[0].message.content.strip()

@app.route("/predict", methods=["POST"])
def predict():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        # Read blob & decode
        blob = request.files["file"].read()
        audio_seg = AudioSegment.from_file(io.BytesIO(blob))
        audio_seg = audio_seg.set_frame_rate(44100).set_channels(1)

        samples = np.array(audio_seg.get_array_of_samples()).astype(np.float32)
        max_val = np.iinfo(audio_seg.array_type).max
        audio_data = samples / max_val
        sample_rate = 44100

        # Extract features & get probabilities
        features = extract_feature(audio_data, sample_rate).reshape(1, -1)
        proba    = model.predict_proba(features)[0]  # array of probabilities
        labels   = encoder.inverse_transform(np.arange(len(proba)))

        # Build a map of emotion→percentage (rounded to 1 decimal)
        emotion_probs = {
            label: round(float(p * 100), 1)
            for label, p in zip(labels, proba)
        }

        # Pick top emotion
        top_idx = int(np.argmax(proba))
        emotion = labels[top_idx]

        # Generate first ChatGPT reply
        reply = generate_initial_reply(emotion)

        # Create new chat session
        chat_id = uuid.uuid4().hex
        conversations[chat_id] = [
            {"role": "system",    "content": "You are a compassionate assistant."},
            {"role": "user",      "content": f"I am feeling {emotion}."},
            {"role": "assistant", "content": reply}
        ]

        return jsonify({
            "emotion":      emotion,
            "probabilities": emotion_probs,
            "reply":        reply,
            "chat_id":      chat_id
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    chat_id = data.get("chat_id")
    user_msg = data.get("message", "").strip()

    if not chat_id or chat_id not in conversations:
        return jsonify({"error": "Invalid or missing chat_id"}), 400
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    # Append user message
    conversations[chat_id].append({"role": "user", "content": user_msg})

    # Get assistant response
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversations[chat_id]
    )
    assistant_msg = resp.choices[0].message.content.strip()

    # Save to history
    conversations[chat_id].append({"role": "assistant", "content": assistant_msg})

    return jsonify({"reply": assistant_msg})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)



# import os
# import uuid
# import pickle
# import traceback
# import io
# import numpy as np
# import openai
# from dotenv import load_dotenv

# from flask import Flask, request, jsonify, render_template, session
# from flask_cors import CORS
# from pydub import AudioSegment
# from prototype import extract_feature
# from sklearn.preprocessing import StandardScaler

# # Load env & set OpenAI key
# load_dotenv()
# openai.api_key = os.getenv("OPENAI_API_KEY")

# # Initialize Flask
# app = Flask(__name__)
# app.secret_key = os.getenv("FLASK_SECRET", "supersecret")
# CORS(app, resources={r"/*": {"origins": [
#     "http://localhost:5173",
#     "https://your-netlify-site.netlify.app"
# ]}})

# # Load your trained model & label encoder
# with open("trained_emotion_model.pkl", "rb") as f:
#     model = pickle.load(f)
# with open("label_encoder.pkl", "rb") as f:
#     encoder = pickle.load(f)

# # In‑memory store of conversations: chat_id → message list
# conversations = {}

# @app.route("/")
# def index():
#     return render_template("index.html")

# def generate_initial_reply(emotion: str) -> str:
#     """First reply based on detected emotion."""
#     system = {
#         "role": "system",
#         "content": "You are a compassionate assistant who responds empathetically to user emotions."
#     }
#     user = {
#         "role": "user",
#         "content": f"I am feeling {emotion}. How would you respond?"
#     }
#     resp = openai.ChatCompletion.create(
#         model="gpt-3.5-turbo",
#         messages=[system, user],
#         max_tokens=100,
#     )
#     return resp.choices[0].message.content.strip()

# @app.route("/predict", methods=["POST"])
# def predict():
#     try:
#         if "file" not in request.files:
#             return jsonify({"error": "No file uploaded"}), 400

#         # Read blob & decode
#         blob = request.files["file"].read()
#         audio_seg = AudioSegment.from_file(io.BytesIO(blob))
#         audio_seg = audio_seg.set_frame_rate(44100).set_channels(1)

#         samples = np.array(audio_seg.get_array_of_samples()).astype(np.float32)
#         max_val = np.iinfo(audio_seg.array_type).max
#         audio_data = samples / max_val
#         sample_rate = 44100

#         # Extract features & predict
#         features = extract_feature(audio_data, sample_rate).reshape(1, -1)
#         label = model.predict(features)[0]
#         emotion = encoder.inverse_transform([label])[0]

#         # Generate first ChatGPT reply
#         reply = generate_initial_reply(emotion)

#         # Create new chat session
#         chat_id = uuid.uuid4().hex
#         conversations[chat_id] = [
#             {"role": "system",    "content": "You are a compassionate assistant."},
#             {"role": "user",      "content": f"I am feeling {emotion}."},
#             {"role": "assistant", "content": reply}
#         ]

#         return jsonify({"emotion": emotion, "reply": reply, "chat_id": chat_id})

#     except Exception as e:
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500

# @app.route("/chat", methods=["POST"])
# def chat():
#     data = request.get_json()
#     chat_id = data.get("chat_id")
#     user_msg = data.get("message", "").strip()

#     if not chat_id or chat_id not in conversations:
#         return jsonify({"error": "Invalid or missing chat_id"}), 400
#     if not user_msg:
#         return jsonify({"error": "Empty message"}), 400

#     # Append user message
#     conversations[chat_id].append({"role": "user", "content": user_msg})

#     # Get assistant response
#     resp = openai.ChatCompletion.create(
#         model="gpt-3.5-turbo",
#         messages=conversations[chat_id]
#     )
#     assistant_msg = resp.choices[0].message.content.strip()

#     # Save to history
#     conversations[chat_id].append({"role": "assistant", "content": assistant_msg})

#     return jsonify({"reply": assistant_msg})

# if __name__ == "__main__":
#     app.run(host="127.0.0.1", port=8000, debug=True)

