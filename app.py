import os
from flask import Flask, request, jsonify, render_template
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

    # Ask GPT to classify emotion
    prompt = (
        "Classify the primary emotion expressed in the following text. "
        "Respond in JSON with keys 'emotion' (one word, e.g. Happy, Sad, Angry, Neutral) "
        "and 'message' (a short empathetic response).\n\n"
        f"Text: \"{text}\""
    )

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            temperature=0.7,
            max_tokens=60,
        )
        content = resp.choices[0].message.content.strip()
        # We expect the model to output something like:
        # {"emotion":"Happy","message":"I can feel your excitement! Keep it going."}
        parsed = {}
        try:
            parsed = json.loads(content)
        except:
            # fallback: parse manually
            lines = [l for l in content.splitlines() if ":" in l]
            for l in lines:
                k,v = l.split(":",1)
                parsed[k.strip().strip('"')] = v.strip().strip('",')
        return jsonify(parsed)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

