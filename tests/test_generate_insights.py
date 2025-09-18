import os
from openai import OpenAI

def generate_insights(summary_json: dict) -> str:
    """
    Sends the summary JSON to Groq LLM and returns HTML insights.
    """
    # GROQ_API_KEY = os.getenv('GROQ_API_KEY')

    # Init Groq client (OpenAI-compatible)
    client = OpenAI(api_key="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", base_url="https://api.groq.com/openai/v1")

    # Prepare system + user messages
    system_prompt = (
      "You are an expert UX analyst. "
      "Analyze the provided JSON summary of application usage. "
      "Do not just restate numbers — instead:"
      "- Identify patterns (what users focus on, what they ignore)."
      "- Highlight problems (low completion rates, bounces, friction)."
      "- Prioritize the 2–3 most critical issues."
      "- Mention 1–2 positive highlights."
      "- Suggest possible reasons or next steps (e.g., 'Budget form is confusing, simplify description field')."
      "Format the output as structured HTML (<h2>, <p>, <ul>, <li>)."
    )

    user_prompt = f"Here is the summary JSON of application usage:\n\n{summary_json}\n\nGenerate insights in HTML format."

    # Call Groq LLM
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # adjust to your available Groq model
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=800,
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    # Static JSON test (replace with your schema later)
    summary_json = {
  "pageUsage": [
    { "page": "itinerary", "avgTime": "8m 16s", "visits": 5 },
    { "page": "notebook", "avgTime": "4m 12s", "visits": 6 },
    { "page": "budget", "avgTime": "56s", "visits": 5 },
    { "page": "dashboard", "avgTime": "19s", "visits": 11 },
    { "page": "auth", "avgTime": "18s", "visits": 12 },
    { "page": "welcome", "avgTime": "11s", "visits": 10 },
    { "page": "home", "avgTime": "11s", "visits": 9 },
    { "page": "todos", "avgTime": "9s", "visits": 4 },
    { "page": "calendar", "avgTime": "2s", "visits": 1 }
  ],
  "topNavigationIssues": [
    { "page": "todos", "issue": "Page bounce", "count": 8 },
    { "page": "notebook", "issue": "Page bounce", "count": 4 },
    { "page": "home", "issue": "Page bounce", "count": 4 },
    { "page": "dashboard", "issue": "Page bounce", "count": 4 },
    { "page": "budget", "issue": "Page bounce", "count": 4 }
  ],
  "formUsage": [
    {
      "page": "/budget",
      "completionRate": 36,
      "avgTime": "13s",
      "issues": [
        "36% abandoned mid-form (description field)",
        "27% failed to submit"
      ]
    },
    {
      "page": "/dashboard",
      "completionRate": 80,
      "avgTime": "2m 33s",
      "issues": ["20% abandoned mid-form (edit-destination field)"]
    },
    {
      "page": "/auth",
      "completionRate": 95,
      "avgTime": "6s",
      "issues": ["5% abandoned mid-form (__next field)"]
    },
    {
      "page": "/budget",
      "completionRate": 100,
      "avgTime": "4m 58s",
      "issues": []
    },
    {
      "page": "/itinerary",
      "completionRate": 100,
      "avgTime": "4m 41s",
      "issues": ["267% failed to submit"]
    }
  ],
  "journeyFriction": [
    { "type": "backtracking", "description": "User returned to a previously visited page", "count": 2 },
    { "type": "shortDwell", "description": "User left page very quickly", "count": 6 },
    { "type": "longDwell", "description": "User stayed too long, possible stall", "count": 1 }
  ],
  "topFields": [
    { "action": "click input location", "count": 45, "page": "itinerary" },
    { "action": "click button Search", "count": 32, "page": "itinerary" },
    { "action": "change input location", "count": 22, "page": "itinerary" },
    { "action": "submit form", "count": 22, "page": "itinerary" },
    { "action": "click button Add Activity", "count": 19, "page": "itinerary" }
  ]
}


    html_output = generate_insights(summary_json)
    print(html_output)
