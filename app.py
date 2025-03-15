from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from flask_cors import CORS
import os
import requests
from langdetect import detect  # Language detection
import google.generativeai as genai  # Gemini Integration
import openai  # DeepSeek Integration

app = Flask(__name__)
CORS(app)

# Environment Variables
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize APIs
genai.configure(api_key=GEMINI_API_KEY)

gemini_model = genai.GenerativeModel("gemini-pro")

# DeepSeek Configuration
openai.api_key = DEEPSEEK_API_KEY
openai.api_base = "https://api.deepseek.com/v1"

# Translation Function (Using Sarvam API)
def translate_text(text, target_lang="en"):
    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}"}
    data = {"text": text, "target_lang": target_lang}
    try:
        response = requests.post("https://api.sarvam.ai/translate", json=data, headers=headers)
        response.raise_for_status()
        return response.json().get("translated_text", text)
    except Exception:
        return text  # Fallback to original text if translation fails

# Loan Advisor Logic
def handle_loan_queries(message):
    if "emi" in message.lower():
        return "📊 To calculate EMI, please provide Principal, Rate, and Tenure."
    elif "loan eligibility" in message.lower():
        return "✅ Eligibility: Stable income, credit score 700+, and low debt ratio."
    elif "repayment options" in message.lower():
        return "🔄 Repayment options: EMI, Lump Sum, Step-up/Step-down plans."
    elif "hello" in message.lower() or "hi" in message.lower():
        return "👋 Hello! Welcome to Loan Advisor Bot. How can I assist you today?"
    elif "loan advice" in message.lower():
        return (
            "💡 Loan Advisory Tips:"
            "- Always compare interest rates before taking a loan."
            "- Ensure you have a stable repayment plan."
            "- Avoid over-borrowing to manage debt efficiently."
        )
    return None

# Gemini AI for Custom Responses
def get_gemini_response(prompt, target_lang="en"):
    try:
        response = gemini_model.generate_content(prompt)
        return translate_text(response.text, target_lang)
    except Exception:
        return "❌ Service unavailable."

# DeepSeek API for Enhanced Response
def get_deepseek_response(prompt, target_lang="en"):
    try:
        response = openai.ChatCompletion.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        return translate_text(response['choices'][0]['message']['content'].strip(), target_lang)
    except Exception as e:
        return "❌ Service unavailable."

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    try:
        incoming_msg = request.values.get("Body", "").strip()
        sender = request.values.get("From", "")
        detected_lang = detect(incoming_msg)

        translated_input = translate_text(incoming_msg, target_lang="en")
        loan_response = handle_loan_queries(translated_input)

        if loan_response:
            reply = translate_text(loan_response, target_lang=detected_lang)
        else:
            # Choose between DeepSeek and Gemini (both enabled)
            reply = get_gemini_response(translated_input, target_lang=detected_lang)

        resp = MessagingResponse()
        resp.message(reply)
        return str(resp)

    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return "✅ Loan Advisor Bot is Live!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
