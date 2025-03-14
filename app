import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Sarvam AI API Key (Add your own key here)
SARVAM_API_KEY = "326bc7a1-07e7-4b99-8b74-0f70369e8a73"

# Dummy user data for conversation flow
user_data = {}

# Root Route for Testing
@app.route("/", methods=["GET"])
def home():
    return "🚀 WhatsApp Loan Advisor Bot is Live!"

# Translation Function using Sarvam AI
def translate_text(text, target_lang="en"):
    url = "https://api.sarvam.ai/translate"
    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}"}
    data = {"text": text, "target_lang": target_lang}

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()  # Raise error if request fails
        return response.json().get("translated_text", text)
    except Exception as e:
        return f"Translation error: {str(e)}"

# Language Detection Function
def detect_language(text):
    url = "https://api.sarvam.ai/detect"
    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}"}
    data = {"text": text}

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json().get("detected_language", "en")
    except Exception as e:
        return "en"

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
