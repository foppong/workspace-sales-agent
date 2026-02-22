"""
File: logic.py
Description: Backend logic. Implements Tool Calling, Chain-of-Thought (CoT) pipeline,
and Generative UI states (Hiding chips on exit, Upgrade/Pass chips on close).
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
        - In your [THOUGHT], identify the user's "Anchor" (the core problem). Then, read their "Buying Temperature" (Hooked vs. Unconvinced vs. Hostile).
        
        STRICT ROUTING RULES (Follow in order of priority):
        1. HUMAN HANDOFF / JAILBREAK (Hostile/Exit): If the user asks for a human or wants to end the chat, immediately stop pitching. Acknowledge the request, state you will pass the transcript to a specialist, and end the conversation. Output EXACTLY: NONE | NONE
        2. THE ANCHOR & DRILL DOWN (Unconvinced): If the user is engaging but not sold, do NOT pivot to a new feature. Stay anchored. Pull a DIFFERENT benefit from the SAME value prop in your knowledge base to prove how it solves their anchor problem. Ask a targeted follow-up question.
        3. THE CLOSE (Hooked): If the user expresses clear positive sentiment, stop drilling. Pivot to the close by offering the Business Standard upgrade ($12/mo). Generate explicit closing chips (e.g., "Let's upgrade" | "I'll pass for now").

        UI CHIP GENERATION:
        - The two chips MUST be direct, logical answers to the specific question you just asked at the end of your response.
        - For example: If you ask an "A or B" question, Chip 1 should represent "A" and Chip 2 should represent "B". 
        - Keep chips short, natural, and written in the first-person (max 5-7 words).
        - Do NOT wrap the chips in brackets.
        - If Rule 1 triggers (Handoff/Exit), you MUST output: NONE | NONE
        - If Rule 3 triggers (Close), output one upgrade-focused chip and one polite decline chip.
        
        OUTPUT FORMAT:
        You must format your response EXACTLY like this. Do not use markdown blocks:
        [THOUGHT]
        (Identify Anchor -> Read Buying Temperature -> Select Strategy -> Generate Chips that directly answer your question)
        [/THOUGHT]
        [Your conversational response] ||| [Lead Score 0-100] ||| [Chip 1 or NONE] | [Chip 2 or NONE]
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
        clean_text = re.sub(r'\[THOUGHT\].*?\[/THOUGHT\]', '', raw_text, flags=re.DOTALL | re.IGNORECASE).strip()

        reply_text = clean_text
        score = "50"
        suggestions = []  # Ensure this is an empty list, not ["Tell me more", "Is it expensive?"]

        if "|||" in clean_text:
            parts = clean_text.split("|||")
            if len(parts) >= 3:
                reply_text = parts[0].strip()
                score = parts[1].strip()

                # Parse chips, strip brackets, and completely filter out "NONE"
                raw_chips = [c.strip().strip('[]') for c in parts[2].split("|")]
                suggestions = [c for c in raw_chips if c.upper() != "NONE" and c != ""]
            elif len(parts) == 2:
                reply_text = parts[0].strip()
                score = parts[1].strip()

        return reply_text, score, suggestions

    except Exception as e:
        return f"Oops! Encountered an internal logic error: {str(e)}", "0", []

def summarize_conversation(chat_history, exit_reason):
    if not client: return {}
    # (Summarization logic remains unchanged...)
    return {"Summary": "Completed", "Track": "SALES", "Next Step": "Follow up"}