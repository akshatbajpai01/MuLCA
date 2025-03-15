from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from flask_cors import CORS
import requests
import time
import os
import traceback
import math  # For EMI calculation
from langdetect import detect  # Language detection for multilingual support
from googletrans import Translator  # Google Translate integration

app = Flask(__name__)
CORS(app)

# Environment Variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")

# API URLs
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Debugging Function
def log_debug_info(stage, data=None, error=None):
    print(f"🟦 DEBUG [{stage}]")
    if data:
        print(f"✅ Data: {data}")
    if error:
        print(f"❌ Error: {error}")

# Google Translate Function
translator = Translator()

def translate_text(text, target_lang="en"):
    try:
        translated_text = translator.translate(text, dest=target_lang).text
        log_debug_info("Google Translate Success", {"Original": text, "Translated": translated_text, "Target": target_lang})
        return translated_text
    except Exception as e:
        log_debug_info("Google Translate Failure", error=str(e))
        return text

# EMI Calculation Function
def calculate_emi(principal, rate, tenure):
    try:
        monthly_rate = rate / (12 * 100)
        emi = (principal * monthly_rate * (1 + monthly_rate) ** tenure) / \
              ((1 + monthly_rate) ** tenure - 1)
        return round(emi, 2)
    except Exception as e:
        log_debug_info("EMI Calculation Failure", error=str(e))
        return "❌ Error calculating EMI."

# Loan-related Queries
def handle_loan_queries(message):
    if "emi" in message.lower():
        try:
            _, principal, rate, tenure = message.split()
            emi = calculate_emi(float(principal), float(rate), int(tenure))
            return f"📈 EMI for ₹{principal} at {rate}% for {tenure} months is ₹{emi}."
        except ValueError:
            return "❌ Incorrect format. Use: 'EMI <Principal> <Rate> <Tenure in months>'"

    elif "loan eligibility" in message.lower():
        return (
            "✅ Loan Eligibility Guide:\n"
            "- Stable income source\n"
            "- Minimum credit score: 700+\n"
            "- Debt-to-income ratio below 40%\n"
            "- Employment stability for 2+ years"
        )

    elif "interest rate" in message.lower():
        return (
            "💰 Typical Loan Interest Rates:\n"
            "- Home Loan: 6.5% - 8.5%\n"
            "- Personal Loan: 10% - 18%\n"
            "- Car Loan: 7% - 12%"
        )

    elif "repayment options" in message.lower():
        return (
            "🔄 Loan Repayment Options:\n"
            "- EMI-based (Monthly Installments)\n"
            "- Bullet Payment (Lump Sum)\n"
            "- Step-up/Step-down EMI Plans"
        )

    return None

# OpenAI Response
def get_openai_response(user_message):
    user_language = detect(user_message)  # Detect language
    translated_input = translate_text(user_message, target_lang="en")

    loan_response = handle_loan_queries(translated_input)
    if loan_response:
        return translate_text(loan_response, target_lang=user_language)

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a financial expert providing guidance on loans, banking, investments, and financial management."},
            {"role": "user", "content": translated_input}
        ]
    }

    try:
        response = requests.post(OPENAI_API_URL, json=data, headers=headers, timeout=20)
        response.raise_for_status()
        openai_response = response.json()["choices"][0]["message"]["content"]
        return translate_text(openai_response, target_lang=user_language)
    except requests.exceptions.RequestException as e:
        log_debug_info("OpenAI API Failure", error=str(e))
        return "❌ Service unavailable."

@app.route("/", methods=["GET"])
def home():
    return "✅ Flask server is running!"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    try:
        incoming_msg = request.values.get("Body", "").strip()
        sender = request.values.get("From", "")

        log_debug_info("Incoming Message", {"Sender": sender, "Message": incoming_msg})

        response_msg = get_openai_response(incoming_msg)
        translated_msg = translate_text(response_msg, target_lang=detect(incoming_msg))

        resp = MessagingResponse()
        resp.message(translated_msg)

        log_debug_info("Reply Sent", {"Reply": translated_msg})
        return str(resp)

    except Exception as e:
        log_debug_info("Server Error", error=str(e))
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    print("🚀 Flask server is running with debugging enabled...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
