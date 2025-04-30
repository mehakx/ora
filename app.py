import os
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__, static_folder="static", template_folder=".")
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Prompt GPT to classify emotion & craft a response in JSON
    prompt = (
        "Classify the primary emotion expressed in the following text as one word "
        "(e.g. Happy, Sad, Angry, Neutral), then write a short empathetic response. "
        "Return output as valid JSON with keys 'emotion' and 'message'.\n\n"
        f"Text: \"{text}\""
    )

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=80,
        )
        content = resp.choices[0].message.content.strip()

        # Try to parse as JSON
        parsed = json.loads(content)
        emotion = parsed.get("emotion", "Neutral")
        message = parsed.get("message", "")

    except json.JSONDecodeError:
        # Fallback: crude manual parse
        emotion = "Neutral"
        message = ""
        for line in content.splitlines():
            if line.lower().startswith("emotion"):
                emotion = line.split(":", 1)[1].strip().strip('"')
            if line.lower().startswith("message"):
                message = line.split(":", 1)[1].strip().strip('"')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"emotion": emotion, "message": message})

if __name__ == "__main__":
    app.run(debug=True)

