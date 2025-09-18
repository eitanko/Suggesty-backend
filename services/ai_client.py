# services/ai_client.py
import os
from openai import OpenAI


def generate_ai_insights(summary: dict) -> str:
    """
    Send the summary JSON to Groq LLM and return HTML insights.
    Requires environment variable GROQ_API_KEY.
    """

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY environment variable")

    # Groq provides an OpenAI-compatible API
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )

    # System prompt to guide the LLM
    system_prompt = (
        "You are a Product Manager analyzing UX analytics data. "
        "Your task is to write a structured, actionable report in HTML "
        "that could be shown directly in a product analytics dashboard. "
        "Do not simply restate numbers. Instead:\n"
        "- Identify usage patterns (core vs. secondary features, ignored features).\n"
        "- Highlight problems (low completion rates, high bounces, friction signals).\n"
        "- Prioritize the 2–3 most critical issues.\n"
        "- Call out 1–2 positive highlights.\n"
        "- Suggest next steps (e.g., 'Simplify the budget form description field').\n"
        "Format the output with <h2>, <h3>, <p>, <ul>, and <li> tags.\n"
    )

    # User prompt with summary JSON
    user_prompt = f"""
    Generate a concise, insightful report based on the following data.
    Format the output with <h2>, <h3>, <p>, <ul>, and <li> tags.
    Take into account that login and welcome pages are friquently used but not core features.
    Here is the summary JSON of application usage:

    {summary}
    """


    # Call the model
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",   # Groq-supported model
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,   # allow a bit more creativity for better narrative
        max_tokens=1200,
    )


    # Extract first choice
    return response.choices[0].message.content
