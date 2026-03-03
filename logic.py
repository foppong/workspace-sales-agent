"""
File: logic.py
Description: Backend logic for Workspace Sales Agent.
Implementation: Solution 2 (State Machine Wrapper).
Separates creative copywriting from rigid UI state enforcement.
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

        # --- 1. PRE-PROCESSING: STATE CLASSIFICATION ---
        low_input = user_input.lower()
        is_ready_state = any(x in low_input for x in ["sign me up", "upgrade me", "let's do this", "how much", "set up"])
        is_hostile_exit = any(x in low_input for x in ["cancel", "human", "stop", "close", "not interested", "no thanks"])

        formatted_contents = []
        for msg in chat_history:
            role = "model" if msg["role"] == "bot" else "user"
            formatted_contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg.get("text", msg.get("content", "")))] )
            )

        # Simplified Prompt focusing on copywriting
        system_prompt = """
        You are an expert Google Workspace Sales Agent upselling 'Business Standard' ($12/user/month) to a Branding Agency.
        
        RULES:
        - If the user wants to exit/cancel/human, be polite and end the chat.
        - If they ask questions, use tools to answer specifically for a branding agency.
        - If they are ready to upgrade, tell them to go to the 'Billing' section of the Admin Console.
        - NEVER feature dump. 
        - End your text with ||| [Readiness Score 0-100] ||| [Chip A] | [Chip B]
        - If ending the conversation, use: ||| 0 ||| NONE | NONE
        """

        final_contents = [types.Content(role="user", parts=[types.Part.from_text(text=system_prompt)])] + formatted_contents
        final_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))

        config = types.GenerateContentConfig(tools=[workspace_tool], temperature=0.1)
        response = client.models.generate_content(model=model_id, contents=final_contents, config=config)

        # TOOL CALL RECOVERY
        if response.candidates[0].content.parts[0].function_call:
            fact_data = get_workspace_fact()
            final_contents.append(response.candidates[0].content)
            final_contents.append(types.Content(role="user", parts=[
                types.Part.from_function_response(name="get_workspace_fact", response={"result": fact_data})]))
            response = client.models.generate_content(model=model_id, contents=final_contents, config=config)

        # --- 2. EXTRACTION ---
        raw_text = "".join([part.text for part in response.candidates[0].content.parts if part.text])
        clean_text = re.sub(r"\[THOUGHT\].*?\[/THOUGHT\]", "", raw_text, flags=re.DOTALL | re.IGNORECASE).strip()

        reply_text = clean_text
        score = "50"
        suggestions = []

        # Parse LLM's attempted formatting
        if "|||" in clean_text:
            parts = clean_text.split("|||")
            reply_text = parts[0].strip()
            score = parts[1].strip() if len(parts) > 1 else "50"
            if len(parts) >= 3:
                raw_chips = [c.strip().strip('[]') for c in parts[2].split("|")]
                suggestions = [c for c in raw_chips if "NONE" not in c.upper() and c != ""]

        # --- 3. THE GUARDRAIL LAYER (Solution 2) ---
        # Detect if the LLM is ending the conversation based on its own text
        is_agent_ending = any(x in reply_text.lower() for x in ["specialist", "reach out", "time", "closing", "goodbye"])

        if is_hostile_exit or is_agent_ending:
            suggestions = [] # Force zero chips for exits
        elif is_ready_state:
            suggestions = ["Upgrade Me", "No Thanks"] # Force Ready chips
        elif not suggestions:
            suggestions = ["Tell me more", "Next steps"] # Fallback chips for engagement

        # --- 4. JUDGE COMPLIANCE: Question Enforcement ---
        # If not an exit, ensure we end with a question mark
        if not is_agent_ending and not is_hostile_exit:
            reply_text = reply_text.strip()
            if not reply_text.endswith('?'):
                if reply_text.endswith(('.', '!')):
                    reply_text += " Does that make sense?"
                else:
                    reply_text += "?"

        return reply_text, score, suggestions

    except Exception as e:
        return f"Oops! Internal error: {str(e)}", "0", []