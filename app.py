from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from flask_cors import CORS
import requests
import time
import os
import traceback

app = Flask(__name__)  # Fixed __name__
CORS(app)

# Get environment variables properly
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")

# API Endpoints
SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

def get_openai_response(user_message):
    if not OPENAI_API_KEY:
        return "❌ OpenAI API Key not found."

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a financial expert providing guidance on loans, banking, investments, and financial management."},
            {"role": "user", "content": user_message}
        ]
    }

    for attempt in range(3):
        try:
            response = requests.post(OPENAI_API_URL, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException:
            time.sleep(2 ** attempt)

    return "❌ Service unavailable."

def translate_text(text, target_lang="hi"):
    if not SARVAM_API_KEY:
        return text

    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}"}
    data = {"text": text, "target_lang": target_lang}

    try:
        response = requests.post(SARVAM_TRANSLATE_URL, json=data, headers=headers)
        response.raise_for_status()
        return response.json().get("translated_text", text)
    except requests.exceptions.RequestException:
        return text

def speech_to_text(audio_url):
    if not SARVAM_API_KEY:
        return "❌ Speech-to-text service unavailable."

    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}"}
    data = {"audio_url": audio_url, "language": "auto"}

    try:
        response = requests.post(SARVAM_STT_URL, json=data, headers=headers)
        response.raise_for_status()
        return response.json().get("transcription", "Could not process audio.")
    except requests.exceptions.RequestException:
        return "Error processing voice message."

def text_to_speech(text, language="en"):
    if not SARVAM_API_KEY:
        return ""

    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}"}
    data = {"text": text, "language": language}

    try:
        response = requests.post(SARVAM_TTS_URL, json=data, headers=headers)
        response.raise_for_status()
        return response.json().get("audio_url", "")
    except requests.exceptions.RequestException:
        return ""

@app.route("/", methods=["GET"])
def home():
    return "✅ Flask server is running!"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    try:
        incoming_msg = request.values.get("Body", "").strip()
        sender = request.values.get("From", "")
        media_url = request.values.get("MediaUrl0", "")

        print(f"📩 Received message from {sender}: {incoming_msg or 'Voice Note'}")

        if media_url:
            text_message = speech_to_text(media_url)
        else:
            text_message = incoming_msg

        response_msg = get_openai_response(text_message)
        translated_msg = translate_text(response_msg, target_lang="hi")

        resp = MessagingResponse()
        audio_url = text_to_speech(translated_msg)

        if audio_url:
            msg = resp.message()
            msg.media(audio_url)
        else:
            resp.message(translated_msg)

        print(f"📤 Replying to {sender}: {translated_msg}")
        return str(resp)

    except Exception as e:
        print(f"❌ Error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":  # Fixed __name__
    print("🚀 Flask server is running...")
    app.run(host="0.0.0.0", port=8080, debug=True)
