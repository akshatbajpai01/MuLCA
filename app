import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Sarvam API Key for translation
SARVAM_API_KEY = "326bc7a1-07e7-4b99-8b74-0f70369e8a73"

# In-memory user data storage
user_data = {}

# ======================= Homepage Route to Fix 404 Error =======================
@app.route("/")
def home():
    return "Welcome to the Loan Advisor Bot! Use WhatsApp to chat with the bot."

# ======================= Translation Function =======================
def translate_text(text, target_lang="hi"):
    url = "https://api.sarvam.ai/translate"
    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}"}
    data = {"text": text, "target_lang": target_lang}

    response = requests.post(url, json=data, headers=headers)
    return response.json().get("translated_text", text)

# ======================= Main WhatsApp Bot Route =======================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    user_phone = request.form.get("From")
    user_message = request.form.get("Body")

    # Translation (Auto-detect to English, then respond in user's language)
    user_lang = "hi"  # Default to Hindi (can add auto-detection if required)
    translated_input = translate_text(user_message, "en")

    # Conversation Logic
    if user_phone not in user_data:
        user_data[user_phone] = {"stage": "employment"}
        response_text = "Are you salaried or self-employed?"
    elif user_data[user_phone]["stage"] == "employment":
        user_data[user_phone]["employment"] = translated_input
        user_data[user_phone]["stage"] = "income"
        response_text = "What is your monthly income?"
    elif user_data[user_phone]["stage"] == "income":
        try:
            user_data[user_phone]["income"] = int(translated_input)
            user_data[user_phone]["stage"] = "credit"
            response_text = "What is your credit score?"
        except ValueError:
            response_text = "Please provide a valid income amount."
    elif user_data[user_phone]["stage"] == "credit":
        try:
            user_data[user_phone]["credit_score"] = int(translated_input)
            income = user_data[user_phone]["income"]
            credit_score = user_data[user_phone]["credit_score"]

            # Loan Eligibility Logic
            if income > 20000 and credit_score > 700:
                response_text = "You are eligible for a loan!"
            else:
                response_text = "Sorry, you may not be eligible."
        except ValueError:
            response_text = "Please provide a valid credit score."

    # Translate response back to user's language
    translated_response = translate_text(response_text, user_lang)

    # Send Response
    resp = MessagingResponse()
    resp.message(translated_response)

    return str(resp)

# ======================= EMI Calculator Function =======================
def calculate_emi(principal, rate, tenure):
    rate = rate / (12 * 100)  # Monthly interest rate
    emi = (principal * rate * ((1 + rate) ** tenure)) / (((1 + rate) ** tenure) - 1)
    return round(emi, 2)

# ======================= Port Binding for Render Deployment =======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Port from Render or default 5000
    app.run(host="0.0.0.0", port=port, debug=True)
