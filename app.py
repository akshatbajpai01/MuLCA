from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from gtts import gTTS
import speech_recognition as sr
import os
import requests

app = Flask(__name__)

# Sarvam AI API endpoint and key
SARVAM_API_URL = "https://api.sarvam.ai/v1/chat"
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "your_sarvam_api_key")

# Twilio credentials
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "your_twilio_account_sid")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "your_twilio_auth_token")


# Root route
@app.route("/")
def home():
    return "Welcome to the Multilingual Loan Advisor!"


# Function to detect language using Sarvam AI
def detect_language(text):
    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "query": f"Detect the language of this text: {text}",
        "language": "en"  # Use English as the default language for the query
    }
    response = requests.post(SARVAM_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get("response", "en")  # Default to English if detection fails
    else:
        return "en"  # Default to English if API call fails


# Function to translate text using Sarvam AI
def translate_text(text, target_language):
    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "query": f"Translate this text to {target_language}: {text}",
        "language": "en"  # Use English as the default language for the query
    }
    response = requests.post(SARVAM_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get("response", text)  # Return original text if translation fails
    else:
        return text  # Return original text if API call fails


# Function to generate text-to-speech
def text_to_speech(text, language):
    tts = gTTS(text=text, lang=language)
    tts.save("response.mp3")
    return "response.mp3"


# Function to convert speech-to-text
def speech_to_text(audio_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return "Could not understand audio"
    except sr.RequestError:
        return "API unavailable"


# Function to get loan advice from Sarvam AI
def get_loan_advice(user_input, language):
    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "query": user_input,
        "language": language
    }
    response = requests.post(SARVAM_API_URL, headers=headers, json=data)
    return response.json().get("response", "Sorry, I couldn't process your request.")


# Twilio webhook for WhatsApp
@app.route("/webhook", methods=['POST'])
def webhook():
    incoming_message = request.form.get('Body')
    user_language = detect_language(incoming_message)

    # Translate input to English for processing
    translated_input = translate_text(incoming_message, 'en')

    # Get loan advice from Sarvam AI
    loan_advice = get_loan_advice(translated_input, 'en')

    # Translate the advice back to the user's language
    translated_advice = translate_text(loan_advice, user_language)

    # Generate text-to-speech response
    speech_file = text_to_speech(translated_advice, user_language)

    # Respond back to the user
    response = MessagingResponse()
    response.message(translated_advice)

    # If the user wants to talk, send the audio file
    if "call" in incoming_message.lower():
        response.message().media(speech_file)

    return str(response)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
