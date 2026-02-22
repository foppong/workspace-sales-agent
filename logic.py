"""
File: logic.py
Description: Backend logic. Implements Tool Calling, Chain-of-Thought (CoT) pipeline,
and strict formatting parsers to prevent text duplication and UI leaks.
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
    try:
        with open("knowledge_base.txt", "r") as f:
            return f.read()
    except Exception as e:
        return "System Error: Knowledge base unavailable."

workspace_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_workspace_fact",
            description="Fetches factual information regarding Google Workspace features including eSignature, Meet Premium, Security Advisor, Appointment Scheduling, and Storage. You MUST use this whenever the user raises a pain point or concern.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "topic": types.Schema(
                        type=types.Type.STRING,
                        description="The category to look up. Choose from: 'pricing', 'scheduling', 'meetings', 'security', 'contracts', 'storage'."
                    )
                },
                required=["topic"]
            )
        )
    ]
)

def get_gemini_response(user_input, chat_history):
    try:
        if not client:
            return "Error: API Key not found. Please check your environment variables.", "0", []

        # --- 2. THE SYSTEM PROMPT ---
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
        - In your [THOUGHT], identify the user's "Anchor" (the core problem). Then, read their "Buying Temperature".
        
        STRICT ROUTING RULES (Follow in order of priority based on the user's MECE conversational state):
        1. TERMINATING STATE (Hostile / Exit / Human Request): The user wants out. Immediately stop pitching. Acknowledge, pass to a specialist, and end chat. You MUST still use the ||| formatting separators, using 'End Chat | End Chat' for the chips.
        2. RESISTING STATE (Price / Competitor / Trust Stalls): The user is evaluating risk, not features. Do not feature-dump. Consult the RAG for policies, discounts (like the 20% off), or trials to lower their barrier to entry. Empathize and ask a clarifying question about their hesitation.
        3. EXPLORING STATE (Unconvinced / Workflow Questions): The user is evaluating capabilities. Stay anchored to their core problem. Fluidly introduce relevant value props from the RAG to prove utility. NEVER use robotic phrasing like "With Business Standard". Speak naturally and ask a targeted discovery question.
        4. READY STATE (Hooked / Positive Sentiment): The user is showing buying intent. Stop drilling. Pivot to the close by offering the upgrade.

        UI CHIP GENERATION:
        - The two chips MUST be direct, logical answers to the specific question you just asked.
        - Do NOT wrap the chips in brackets.
        - If Rule 1 triggers (Handoff/Exit), you MUST output exactly: End Chat | End Chat
        - If Rule 3 triggers (Close), output one upgrade-focused chip and one polite decline chip.

        OUTPUT FORMAT:
        You must format your response EXACTLY like this. Do not use markdown blocks:
        [THOUGHT]
        (Identify Anchor -> Read Buying Temperature -> Select Strategy -> Generate Chips that directly answer your question)
        [/THOUGHT]
        [Your conversational response] ||| [Lead Score 0-100] ||| [Chip 1] | [Chip 2]
        """

        contents = [{"role": "user", "parts": [{"text": system_prompt}]}]
        for msg in chat_history:
            role = "model" if msg["role"] == "bot" else "user"
            contents.append({"role": role, "parts": [{"text": msg["text"]}]})

        contents.append({"role": "user", "parts": [{"text": user_input}]})

        config = types.GenerateContentConfig(
            tools=[workspace_tool],
            temperature=0.1
        )

        response = client.models.generate_content(model=model_id, contents=contents, config=config)

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

        raw_text = response.text or "Error: The AI returned an empty response."

        # BULLETPROOF PARSER: Physically split to guarantee no [/THOUGHT] leak or duplication
        if "[/THOUGHT]" in raw_text.upper():
            # Takes only the text AFTER the thought block
            clean_text = re.split(r'\[/THOUGHT\]', raw_text, flags=re.IGNORECASE)[-1].strip()
        else:
            clean_text = raw_text.strip()

        # Failsafe: Remove literal "NONE | NONE" if LLM hallucinates it into the chat message
        clean_text = clean_text.replace("NONE | NONE", "").strip()

        reply_text = clean_text
        score = "50"
        suggestions = []

        if "|||" in clean_text:
            parts = clean_text.split("|||")
            if len(parts) >= 3:
                reply_text = parts[0].strip()
                score = parts[1].strip()

                # Parse chips and strip brackets
                raw_chips = [c.strip().strip('[]') for c in parts[2].split("|")]
                suggestions = [c for c in raw_chips if c != ""]
            elif len(parts) == 2:
                reply_text = parts[0].strip()
                score = parts[1].strip()
        else:
            # FALLBACK: If LLM forgets the ||| separators during a handoff
            reply_text = clean_text
            if "End Chat" in clean_text:
                suggestions = ["End Chat"]

            # SCRUBBER: Physically remove the literal chip text from the chat bubble if it leaked
        reply_text = re.sub(r'End Chat\s*\|\s*End Chat', '', reply_text, flags=re.IGNORECASE).strip()
        reply_text = reply_text.replace("NONE | NONE", "").strip()

        return reply_text, score, suggestions

    except Exception as e:
        return f"Oops! Encountered an internal logic error: {str(e)}", "0", []

def summarize_conversation(chat_history, exit_reason):
    if not client: return {}
    return {"Summary": "Completed", "Track": "SALES", "Next Step": "Follow up"}