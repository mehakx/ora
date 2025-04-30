import os
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import openai
from dotenv import load_dotenv

# Load your .env variables, including OPENAI_API_KEY
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

    # Build prompt for GPT to classify emotion + craft response
    prompt = (
        "Classify the primary emotion in the text below as one word "
        "(e.g. Happy, Sad, Angry, Neutral), then write a short empathetic response. "
        "Return the result as valid JSON with keys 'emotion' and 'message'.\n\n"
        f"Text: \"{text}\""
    )

    try:
        # Call OpenAI
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=80,
        )
        content = resp.choices[0].message.content.strip()

        # Parse JSON output
        parsed = json.loads(content)
        emotion = parsed.get("emotion", "Neutral")
        message = parsed.get("message", "")

    except json.JSONDecodeError:
        # If GPT didn’t return strict JSON, do a simple fallback parse
        emotion = "Neutral"
        message = ""
        for line in content.splitlines():
            if line.lower().startswith("emotion"):
                emotion = line.split(":", 1)[1].strip().strip('"')
            if line.lower().startswith("message"):
                message = line.split(":", 1)[1].strip().strip('"')
    except Exception as e:
        # Log full stack trace for debugging on Render
        app.logger.error("Error in /analyze", exc_info=e)
        return jsonify({"error": str(e)}), 500

    return jsonify({"emotion": emotion, "message": message})


if __name__ == "__main__":
    app.run(debug=True)
