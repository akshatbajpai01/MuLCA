import os
import base64
import json
from google.cloud import translate_v2 as translate
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

# Initialize Flask app
app = Flask(__name__)

# Initialize user data storage
user_data = {}

# Load Google Cloud credentials from environment variable
def load_google_credentials():
    try:
        # Get the base64-encoded credentials from the environment variable
        encoded_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not encoded_creds:
            raise ValueError("Google Cloud credentials not found in environment variables.")

        # Decode the base64 string
        decoded_creds = base64.b64decode(encoded_creds).decode("utf-8")

        # Write the credentials to a temporary file
        with open("temp_creds.json", "w") as f:
            f.write(decoded_creds)

        # Set the environment variable to point to the temporary file
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "temp_creds.json"

    except Exception as e:
        print(f"Error loading Google Cloud credentials: {e}")
        raise

# Load Google Cloud credentials when the app starts
load_google_credentials()

# Initialize Google Cloud Translation client
translate_client = translate.Client()

# Translation Function
def translate_text(text, target_lang="en"):
    try:
        result = translate_client.translate(text, target_language=target_lang)
        return result['translatedText']
    except Exception as e:
        print(f"Translation error: {str(e)}")  # Log the error
        return "Translation service is currently unavailable. Please try again later."

# Language Detection Function
def detect_language(text):
    try:
        result = translate_client.detect_language(text)
        return result['language']
    except Exception as e:
        print(f"Language detection error: {str(e)}")  # Log the error
        return "en"  # Fallback to English if detection fails

# Home Route
@app.route("/", methods=["GET"])
def home():
    return "🚀 WhatsApp Loan Advisor Bot is Live!"

# WhatsApp Webhook Route
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    user_phone = request.form.get("From")
    user_message = request.form.get("Body")

    # Detect user's language
    user_lang = detect_language(user_message)

    # Translate user input to English for internal processing
    translated_input = translate_text(user_message, "en")

    # Conversation flow logic
    if user_phone not in user_data:
        user_data[user_phone] = {"stage": "employment"}
        response_text = "Are you salaried or self-employed?"
    elif user_data[user_phone]["stage"] == "employment":
        user_data[user_phone]["employment"] = translated_input
        user_data[user_phone]["stage"] = "income"
        response_text = "What is your monthly income?"
    elif user_data[user_phone]["stage"] == "income":
        user_data[user_phone]["income"] = int(translated_input)
        user_data[user_phone]["stage"] = "credit"
        response_text = "What is your credit score?"
    elif user_data[user_phone]["stage"] == "credit":
        user_data[user_phone]["credit_score"] = int(translated_input)
        response_text = "Checking loan eligibility..."

        income = user_data[user_phone]["income"]
        credit_score = user_data[user_phone]["credit_score"]

        if income > 20000 and credit_score > 700:
            response_text = "You are eligible for a loan!"
        else:
            response_text = "Sorry, you may not be eligible."

    # Translate response back to user's language
    translated_response = translate_text(response_text, user_lang)

    # Send response
    resp = MessagingResponse()
    resp.message(translated_response)

    return str(resp)

# Run the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
