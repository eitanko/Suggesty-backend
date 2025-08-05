import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')


def classify_button(data):
    """Classify button click events using GROQ API"""

    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY not found in environment variables")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    # Your classification logic here
    # This is a placeholder - implement your actual classification logic

    try:
        # Make API call to GROQ
        # Replace with your actual API endpoint and payload
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",  # Replace with actual endpoint
            headers=headers,
            json=data
        )

        if response.status_code == 200:
            result = response.json()
            return result.get('label', 'unknown')
        else:
            raise Exception(f"API request failed: {response.status_code}")

    except Exception as e:
        raise Exception(f"Classification failed: {str(e)}")