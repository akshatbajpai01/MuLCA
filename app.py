import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google.cloud import translate_v2 as translate

# Create a temporary JSON file from the environment variable on Render
with open("key.json", "w") as key_file:
    key_file.write(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
# Load the JSON key file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "E:\\key\\mulca-453508-413ed3cd3277.json"

# Initialize Google Translate Client
translate_client = translate.Client()

def translate_text(text, target_lang="en"):
    try:
        result = translate_client.translate(text, target_language=target_lang)
        return result['translatedText']
    except Exception as e:
        print(f"❌ Translation Error: {str(e)}")
        return "Error in translation. Please try again."

app = Flask(__name__)

# Dictionary to track user conversations
user_data = {}

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    user_phone = request.form.get("From")
    user_message = request.form.get("Body")

    # Translate user input to English for easier processing
    translated_input = translate_text(user_message, "en")

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

    # Translate the bot's response back to the user's language
    translated_response = translate_text(response_text, "hi")  # Change 'hi' to user’s language if needed

    resp = MessagingResponse()
    resp.message(translated_response)

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
