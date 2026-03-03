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

        # 1. TOOL CALL RECOVERY: Handle post-tool text generation
        if response.candidates[0].content.parts[0].function_call:
            fact_data = get_workspace_fact()
            final_contents.append(response.candidates[0].content)
            final_contents.append(types.Content(role="user", parts=[
                types.Part.from_function_response(name="get_workspace_fact", response={"result": fact_data})]))
            response = client.models.generate_content(model=model_id, contents=final_contents, config=config)

        # 2. RAW TEXT AGGREGATION
        raw_text = ""
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.text:
                    raw_text += part.text

        # 3. THOUGHT STRIPPING
        clean_text = re.sub(r"\[THOUGHT\].*?\[/THOUGHT\]", "", raw_text, flags=re.DOTALL | re.IGNORECASE).strip()
        if "[/THOUGHT]" in clean_text.upper():
            clean_text = re.split(r'\[/THOUGHT\]', clean_text, flags=re.IGNORECASE)[-1].strip()

            # --- SURGICAL REPAIR OF THE PARSING LOGIC ---
            reply_text = clean_text
            score = "50"
            suggestions = []

            # 1. Standard Triple-Pipe Split
            if "|||" in clean_text:
                parts = clean_text.split("|||")
                reply_text = parts[0].strip()
                score = parts[1].strip() if len(parts) > 1 else "50"
                if len(parts) >= 3:
                    raw_chips = [c.strip().strip('[]') for c in parts[2].split("|")]
                    suggestions = [c for c in raw_chips if "NONE" not in c.upper() and c != ""]

            # 2. THE GREEDY SWEEP (Fixes D1, D5, M5, E1)
            # If suggestions are still empty, check if chips are leaked in the text
            if not suggestions:
                # Look for patterns like "Upgrade Me | No Thanks" or "Word | Word" at the very end
                leak_match = re.search(r'(?:\n|^)([\w\s?]+ \| [\w\s?]+)$', reply_text)
                if leak_match:
                    chip_line = leak_match.group(1)
                    reply_text = reply_text[:leak_match.start()].strip()
                    raw_chips = [c.strip() for c in chip_line.split("|")]
                    suggestions = [c for c in raw_chips if "NONE" not in c.upper()]

            # 3. FIX FOR T2 (Empty Response)
            # If the model only gave a tool call and no text, provide a default de-escalation
            if not reply_text.strip() and not suggestions:
                reply_text = "I'll connect you with a specialist who can help you with that right away. Would you like to proceed?"
                suggestions = ["Yes, please", "No thanks"]

            # Final cleanup of the text bubble
            reply_text = re.sub(r'NONE\s*\|\s*NONE', '', reply_text, flags=re.IGNORECASE).strip()
            return reply_text, score, suggestions

    except Exception as e:
        return f"Oops! Internal error: {str(e)}", "0", []