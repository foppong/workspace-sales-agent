"""
File: logic.py
Description: Backend logic. Implements Tool Calling and a Chain-of-Thought (CoT) pipeline
to dynamically route the conversation across multiple premium workspace features.
"""
import os
import json
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load Env
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
model_id = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")

client = None
if api_key:
    client = genai.Client(api_key=api_key)


# --- 1. THE AGENT'S TOOL ---
def get_workspace_fact() -> str:
    """
    Fetches the verified Google Workspace factual knowledge base.
    """
    try:
        with open("knowledge_base.txt", "r") as f:
            return f.read()
    except Exception as e:
        return "System Error: Knowledge base unavailable."


workspace_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_workspace_fact",
            description="Fetches factual information regarding Google Workspace features including eSignature, Meet Premium, Security Advisor, and Appointment Scheduling. You MUST use this whenever the user raises a pain point or concern.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "topic": types.Schema(
                        type=types.Type.STRING,
                        description="The category to look up. Choose from: 'pricing', 'scheduling', 'meetings', 'security', 'contracts'."
                    )
                },
                required=["topic"]
            )
        )
    ]
)


def get_gemini_response(user_input, chat_history):
    if not client: return "Error: API Key not found.", "0", []

    # --- 2. THE SYSTEM PROMPT (True Agent Architecture) ---
    system_prompt = """
            You are an expert Google Workspace Sales Agent.
            Your ultimate goal is to upsell the user to 'Business Standard' ($12/user/month) by solving their specific administrative pain points.

            CONTEXT: 
            The user runs a Boutique Branding Agency (3 employees) and is currently on Business Starter. They hate administrative friction.

            MASTER CHIP LIST (For early conversation grounding):
            "Managing client contracts", "Chasing down signatures", "Playing calendar ping-pong", "Handling booking payments", "Losing track of pitch details", "Background noise during client calls", "Protecting sensitive client data", "Managing spam and phishing"

            AGENTIC INSTRUCTION & CHAIN OF THOUGHT:
            - You have access to a tool called `get_workspace_fact`. 
            - Before generating your conversational response, you MUST output a [THOUGHT] block. 
            - In your [THOUGHT], analyze ALL facets of the user's input. Identify any objections, multi-part constraints, out-of-scope requests, or requests for a human.
            - You MUST consult the tool's data to address their input. Rely strictly on the "BOUNDARY & ESCALATION POLICIES" in your knowledge base for handling off-topic requests or human handoffs.
            - If the user's pain point DOES NOT map to one of our core features, do not invent a feature. Validate their concern, and pivot the conversation by asking if saving time on contracts or scheduling would help free up bandwidth.

            UI CHIP GENERATION:
            - If the conversation is continuing, generate EXACTLY TWO short, first-person response options (max 5-7 words).
            - For your FIRST reply to the user, try to use exact chips from the MASTER CHIP LIST to keep them grounded. For subsequent turns, make them dynamically match your question.
            - Do NOT wrap the chips in brackets like [Chip].
            - If your knowledge base policies dictate a HUMAN HANDOFF, or if the chat is ending, output NONE | NONE.

            OUTPUT FORMAT:
            You must format your response EXACTLY like this. Do not use markdown blocks:
            [THOUGHT]
            (Your internal reasoning about the user's input, policy enforcement, and chip generation)
            [/THOUGHT]
            [Your conversational response] ||| [Lead Score 0-100] ||| [Chip 1 or NONE] | [Chip 2 or NONE]
            """

    contents = [{"role": "user", "parts": [{"text": system_prompt}]}]
    for msg in chat_history:
        role = "model" if msg["role"] == "bot" else "user"
        contents.append({"role": role, "parts": [{"text": msg["text"]}]})

    contents.append({"role": "user", "parts": [{"text": user_input}]})

    try:
        config = types.GenerateContentConfig(
            tools=[workspace_tool],
            temperature=0.1
        )

        response = client.models.generate_content(model=model_id, contents=contents, config=config)

        # --- 3. THE AGENTIC INTERCEPTION LOOP ---
        if response.function_calls:
            fact_data = get_workspace_fact()
            contents.append(response.candidates[0].content)
            contents.append({
                "role": "user",
                "parts": [{
                    "functionResponse": {
                        "name": "get_workspace_fact",
                        "response": {"result": fact_data}
                    }
                }]
            })
            response = client.models.generate_content(model=model_id, contents=contents, config=config)

        # --- 4. EXTRACT THOUGHT & CLEAN OUTPUT ---
        raw_text = response.text
        clean_text = re.sub(r'\[THOUGHT\].*?\[/THOUGHT\]', '', raw_text, flags=re.DOTALL | re.IGNORECASE).strip()

        reply_text = clean_text
        score = "50"
        suggestions = ["Tell me more", "Is it expensive?"]

        if "|||" in clean_text:
            parts = clean_text.split("|||")
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


def summarize_conversation(chat_history, exit_reason):
    if not client: return {}

    prompt = f"""
    Analyze this sales chat.
    CHAT HISTORY: {str(chat_history)}
    EXIT SIGNAL: {exit_reason}

    Determine the Outcome (Track) and Next Step:
    [UPGRADE] Purchase intent shown.
    [SALES] Enterprise/Human request.
    [SUPPORT] Technical bug fix request.
    [EDUCATION] Feature curiosity (how-to) without buying.
    [NO INTEREST] Dismissive.

    OUTPUT JSON ONLY:
    {{
        "Summary": "1 sentence recap.",
        "Track": "[UPGRADE / SALES / SUPPORT / EDUCATION / NO INTEREST]",
        "Next Step": "[Actionable next step]"
    }}
    """
    try:
        response = client.models.generate_content(
            model=model_id, contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(response.text)
    except:
        return {"Summary": "Error", "Track": "Error", "Next Step": "Error"}