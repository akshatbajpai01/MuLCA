from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from flask_cors import CORS
import requests
import os
import traceback
import google.generativeai as genai
import speech_recognition as sr
from pydub import AudioSegment
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# ✅ Manually set FFmpeg path for pydub
AudioSegment.converter = r"E:\python_works\ff\ffmpeg\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"

# Load API keys securely
load_dotenv(dotenv_path="tests/apis.env")

app = Flask(__name__)
CORS(app)

# Securely load API keys from environment variables
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

# API URLs
SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"
SARVAM_TTS_URL = "https://api.sarvam.ai/tts"

# Configure Google Gemini AI
model = None
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('models/gemini-1.5-pro-002')
        print("✅ Gemini AI model initialized successfully.")
    except Exception as e:
        print(f"❌ Model Initialization Error: {e}")


# ✅ Root Route to confirm service is live
@app.route("/", methods=["GET"])
def home():
    return "✅ The Financial Chatbot is Live! Use the /whatsapp endpoint for interactions."


# ✅ Function to get financial advice from Gemini AI
def get_gemini_response(user_message):
    if not GOOGLE_API_KEY or not model:
        return ["Sorry, the AI service is currently unavailable."]

    try:
        response = model.generate_content(f"You are a financial expert providing guidance on loans, banking, investments, and financial management.\n\nUser Query: {user_message}")

        if response and response.text.strip():
            return [response.text.strip()]
        else:
            return ["Sorry, I couldn't process your request."]

    except Exception as e:
        print(f"❌ Error in Gemini response: {e}")
        return ["Sorry, I couldn't process your request at the moment."]


# ✅ Function to translate text using Sarvam AI
def translate_text(text, target_lang="hi"):
    if not SARVAM_API_KEY:
        return text
    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}", "Content-Type": "application/json"}
    data = {"text": text, "target_lang": target_lang}
    try:
        response = requests.post(SARVAM_TRANSLATE_URL, json=data, headers=headers)
        response.raise_for_status()
        return response.json().get("translated_text", text)
    except requests.exceptions.RequestException as e:
        print(f"❌ Translation Error: {e}")
        return text


# ✅ Function to download and convert Twilio audio to WAV for Google STT
def download_audio(audio_url, output_path="audio_input.wav"):
    temp_path = "temp_audio"
    try:
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            print("❌ Twilio credentials missing!")
            return None

        response = requests.get(audio_url, auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), stream=True)
        response.raise_for_status()

        with open(temp_path, "wb") as audio_file:
            for chunk in response.iter_content(chunk_size=1024):
                audio_file.write(chunk)

        audio = AudioSegment.from_file(temp_path)
        audio.export(output_path, format="wav")
        return output_path
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ✅ Function to convert speech to text using Google STT
def google_speech_to_text(audio_url):
    try:
        wav_path = download_audio(audio_url)
        if not wav_path:
            return "Sorry, I couldn't process the audio."

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio)
        os.remove(wav_path)
        return text
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand the audio."
    except sr.RequestError as e:
        return f"❌ STT Service Error: {e}"
    except Exception as e:
        print(f"❌ Google STT Error: {e}")
        return "Sorry, I couldn't transcribe the audio."


# ✅ WhatsApp Webhook Route
@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    try:
        incoming_msg = request.values.get("Body", "").strip()
        media_url = request.values.get("MediaUrl0", "")
        sender = request.values.get("From", "")
        language = request.values.get("Language", "en")

        print(f"📩 Received from {sender}: {incoming_msg}")

        if media_url:
            incoming_msg = google_speech_to_text(media_url)
            if not incoming_msg:
                return str(MessagingResponse().message("Sorry, I couldn't process the audio."))

        if not incoming_msg:
            return str(MessagingResponse().message("Please send a valid message."))

        gemini_responses = get_gemini_response(incoming_msg)

        resp = MessagingResponse()
        for msg in gemini_responses:
            translated_msg = translate_text(msg, target_lang=language)
            resp.message(translated_msg)

        print(f"📤 Sending reply: {gemini_responses}")
        return str(resp)

    except Exception as e:
        print(f"❌ Error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal Server Error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
