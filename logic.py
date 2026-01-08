"""
File: logic.py
Description: Backend logic.
Updates: Generates DYNAMIC Suggestion Chips based on conversation context.
"""
import os
import random
import json
from google import genai
from dotenv import load_dotenv

# Load Env
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
model_id = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")

client = None
if api_key:
    client = genai.Client(api_key=api_key)

# --- Business Rules ---
MAX_SEATS = 10

def generate_random_profiles():
    """Generates 3 random Micro-SMB profiles."""
    industries = ["Freelance Graphix", "Corner Bakery", "Mobile Car Wash", "Family Law Firm", "Solo Dentist", "IT Fix-it Shop"]
    sizes = ["Solopreneur (1 seat)", "Partnership (2 seats)", "Tiny Team (3 seats)", "Family Biz (5 seats)"]
    pain_points = [
        ("Storage Full", "Heavy Drive usage, hitting 30GB limit. Cannot upload new client videos."),
        ("Meeting Limits", "Webinars limited to 100 people. Need higher capacity for town halls."),
        ("Professionalism", "Using @gmail.com is hurting brand trust. Wants custom domain."),
        ("Security", "Worried about ex-employees retaining access to files.")
    ]

    profiles = []
    selected_industries = random.sample(industries, 3)

    for ind in selected_industries:
        size = random.choice(sizes)
        pp, pp_desc = random.choice(pain_points)
        sku = "Business Starter" if "seats" in size else "Personal Gmail"
        profiles.append({
            "name": f"{ind}", "industry": ind, "size": size,
            "pain_point_title": pp, "pain_point_desc": pp_desc,
            "current_sku": sku,
            "goal": f"Fix {pp.lower()} issues and scale business."
        })
    return profiles

def get_gemini_response(user_input, profile, chat_history):
    """
    Simulates a Challenger Sale rep AND generates context-aware user replies.
    Returns: (text_response, lead_score, list_of_suggestions)
    """
    if not client: return "Error: API Key not found.", "0", []

    system_prompt = f"""
    You are an elite Google Workspace Sales Rep. 
    CONTEXT: {profile['industry']} | {profile['size']} | Pain: {profile['pain_point_desc']}
    
    YOUR STYLE (The "Challenger Sale" approach):
    1. BE CONCISE. 1-2 sentences max.
    2. VALIDATE & PIVOT. Acknowledge the pain, then bridge to solution. 
    3. DRIVE THE SALE. Pivot to 'Business Standard' ($12/seat).
    
    OUTPUT FORMAT:
    Response text ||| Lead Score (0-100) ||| Suggestion1 | Suggestion2 | Suggestion3
    
    The 3 Suggestions should be short (2-4 words) possible replies the USER might say next.
    Example:
    That sounds tough. Most agencies upgrade to Standard for 2TB storage. ||| 40 ||| How much is it? | I don't have budget | Tell me more
    """

    contents = [{"role": "user", "parts": [{"text": system_prompt}]}]
    for msg in chat_history:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    contents.append({"role": "user", "parts": [{"text": user_input}]})

    try:
        response = client.models.generate_content(model=model_id, contents=contents)
        text = response.text

        # Default values
        reply_text = text
        score = "50"
        suggestions = ["Tell me more", "Is it expensive?", "Not interested"]

        if "|||" in text:
            parts = text.split("|||")
            if len(parts) >= 3:
                reply_text = parts[0].strip()
                score = parts[1].strip()
                suggestions = [s.strip() for s in parts[2].split("|")]
            elif len(parts) == 2:
                reply_text = parts[0].strip()
                score = parts[1].strip()

        return reply_text, score, suggestions

    except Exception as e:
        return f"Connection Error: {str(e)}", "0", []

def summarize_conversation(profile, chat_history, exit_reason):
    """Categorizes the conversation based on Gold Use Case examples."""
    if not client: return {}

    prompt = f"""
    Analyze this sales chat with {profile['industry']}.
    CHAT HISTORY: {str(chat_history)}
    EXIT SIGNAL: {exit_reason}

    Determine the Outcome (Track) and Next Step based on Gold Use Cases:
    [UPGRADE] Purchase intent shown.
    [SALES] Enterprise/Human request.
    [SUPPORT] Technical bug fix request.
    [EDUCATION] Feature curiosity (how-to) without buying.
    [NO INTEREST] Dismissive.

    OUTPUT JSON ONLY:
    {{
        "Summary": "1 sentence recap.",
        "Track": "[UPGRADE / SALES / SUPPORT / EDUCATION / NO INTEREST]",
        "Next Step": "[Actionable next step]",
        "Tactics": "1. [Tactic]\\n2. [Tactic]\\n3. [Tactic]"
    }}
    """

    try:
        response = client.models.generate_content(
            model=model_id, contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(response.text)
    except:
        return {"Summary": "Error", "Track": "Error", "Next Step": "Error", "Tactics": "N/A"}