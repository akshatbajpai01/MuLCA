import requests
from google.cloud import translate_v2 as translate
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os

app = Flask(__name__)

# Write the JSON key file from the environment variable
with open("mulca-453508-413ed3cd3277.json", "w") as key_file:
    key_file.write(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])


# Google Cloud Translation Setup
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "E:\\key\\mulca-453508-413ed3cd3277.json"
translate_client = translate.Client()

# Translation Function
def translate_text(text, target_lang="en"):
    try:
        result = translate_client.translate(text, target_language=target_lang)
        return result['translatedText']
    except Exception as e:
        return f"Translation error: {str(e)}"

# Language Detection Function
def detect_language(text):
    try:
        result = translate_client.detect_language(text)
        return result['language']
    except Exception as e:
        return "en"

@app.route("/", methods=["GET"])
def home():
    return "🚀 WhatsApp Loan Advisor Bot is Live!"

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

# Flask app runs on port 5000 or Render-assigned port
if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
