"""
File: logic.py
Description: Backend logic for Workspace Sales Agent.
Implements a 5-stage MECE state machine with a hidden signal for zero-chip UI states.
"""
import os
import json
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
model_id = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")

client = None
if api_key:
    client = genai.Client(api_key=api_key)

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
            description="Fetches factual information regarding Google Workspace features.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"topic": types.Schema(type=types.Type.STRING)},
                required=["topic"]
            )
        )
    ]
)

def get_gemini_response(user_input, chat_history):
    try:
        if not client:
            return "Error: API Key not found.", "0", []

        formatted_contents = []
        for msg in chat_history:
            role = "model" if msg["role"] == "bot" else "user"
            formatted_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg.get("text", msg.get("content", "")))]
                )
            )

        system_prompt = """
        You are an expert Google Workspace Sales Agent.
        Goal: Upsell to 'Business Standard' ($12/user/month) for a Branding Agency.

        STRICT ROUTING RULES (Priority Order):
        1. TERMINATING STATE (Hostile / Exit / Human Request): Stop pitching. Acknowledge and end.
           - Signal: NONE | NONE
        2. RESISTING / EXPLORING STATE: Answer specific questions via RAG before discovery.
        3. NEGATIVE STATE (Soft Refusal): User is "fine as is" or "not interested." 
           - Action: Acknowledge, offer a specialist for later, and end gracefully.
           - Signal: NONE | NONE
        4. ALIGNMENT STATE: User likes a feature. Validate their specific agency use-case.
        5. READY STATE (Logistics): User asks "How?", "Price?", or "Upgrade me."
           - Action: Answer directly (Self-serve in Admin Console). Do NOT pitch more.
           - Signal: Upgrade Me | No Thanks

        UI CHIP POLICY:
        - If the state is TERMINATING or NEGATIVE, use the signal: NONE | NONE
        - Otherwise, provide two 1-3 word chips.
        """

        final_contents = [types.Content(role="user", parts=[types.Part.from_text(text=system_prompt)])] + formatted_contents
        final_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))

        config = types.GenerateContentConfig(tools=[workspace_tool], temperature=0.1)
        response = client.models.generate_content(model=model_id, contents=final_contents, config=config)

        if response.candidates[0].content.parts[0].function_call:
            fact_data = get_workspace_fact()
            final_contents.append(response.candidates[0].content)
            final_contents.append(types.Content(role="user", parts=[types.Part.from_function_response(name="get_workspace_fact", response={"result": fact_data})]))
            response = client.models.generate_content(model=model_id, contents=final_contents, config=config)

        raw_text = response.text or ""
        clean_text = re.split(r'\[/THOUGHT\]', raw_text, flags=re.IGNORECASE)[-1].strip()

        reply_text = clean_text
        score = "50"
        suggestions = []

        if "|||" in clean_text:
            parts = clean_text.split("|||")
            reply_text = parts[0].strip()
            score = parts[1].strip() if len(parts) > 1 else "50"

            if len(parts) >= 3:
                # The logic: if the LLM says "NONE", we return an empty list (NO chips)
                raw_chips = [c.strip() for c in parts[2].split("|")]
                suggestions = [c for c in raw_chips if "NONE" not in c.upper() and c != ""]

        # Scrub any accidental signal leaks from the final text
        reply_text = re.sub(r'NONE\s*\|\s*NONE', '', reply_text, flags=re.IGNORECASE).strip()
        return reply_text, score, suggestions

    except Exception as e:
        return f"Oops! Internal error: {str(e)}", "0", []