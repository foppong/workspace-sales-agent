"""
File: logic.py
Description: Final production-ready logic for Workspace Sales Agent.
Implementation: JSON Mode with Binary State Enforcement and M3 Fix.
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
                types.Content(role=role, parts=[types.Part.from_text(text=msg.get("text", msg.get("content", "")))] )
            )

        system_prompt = """
        You are an expert Google Workspace Sales Agent. 
        Target: Business Standard ($12/user/month) for SMBs on Business Starter.

        [CHIP LOGIC RULES]
        1. BINARY: If you ask a closed-ended confirmation question (e.g. "Does that make sense?", "Ready to proceed?"), chips MUST be ["Yes", "No"].
        2. READY: User wants to sign up/trial. Chips: ["Upgrade Me", "No Thanks"].
        3. EXIT: User says "Stop", "Human", "Dealbreaker", or "Complain". Chips: [].
        4. DISCOVERY: Otherwise, use 1-3 word specific topic chips.

        OUTPUT FORMAT (JSON ONLY):
        {
          "text": "Your response ending in a question",
          "score": "0-100",
          "chips": ["Chip A", "Chip B"]
        }
        """

        final_contents = [types.Content(role="user", parts=[types.Part.from_text(text=system_prompt)])] + formatted_contents
        final_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))

        config = types.GenerateContentConfig(
            tools=[workspace_tool],
            temperature=0.1,
            response_mime_type="application/json"
        )

        response = client.models.generate_content(model=model_id, contents=final_contents, config=config)

        if response.candidates and response.candidates[0].content.parts[0].function_call:
            fact_data = get_workspace_fact()
            final_contents.append(response.candidates[0].content)
            final_contents.append(types.Content(role="user", parts=[
                types.Part.from_function_response(name="get_workspace_fact", response={"result": fact_data})]))
            response = client.models.generate_content(model=model_id, contents=final_contents, config=config)

        data = json.loads(response.text)
        reply_text = data.get("text", "").strip()
        score = data.get("score", "50")
        suggestions = data.get("chips", [])

        # Hard-coded Emergency Brake for Hostility/Dealbreakers (Fixes M3)
        hostile_triggers = ["human", "dealbreaker", "stop pitching", "complain", "bill", "cancel"]
        if any(x in user_input.lower() for x in hostile_triggers):
            suggestions = []
            score = "0"

        return reply_text, score, suggestions

    except Exception as e:
        return f"I'm having a bit of trouble with that. Could you try again?", "0", []