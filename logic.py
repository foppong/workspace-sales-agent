"""
File: logic.py
Description: Backend logic for Workspace Sales Agent using Structured JSON Output.
Implementation: JSON Mode. Ensures 100% UI stability by forcing structured data
from the model, avoiding brittle regex parsing.
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

        # UPDATED PROMPT: Defines the JSON schema and core behaviors
        system_prompt = """
        You are an expert Google Workspace Sales Agent upselling 'Business Standard' ($12/user/month) for a Branding Agency.
        
        OUTPUT FORMAT: Return ONLY a JSON object with:
        {
          "text": "Your conversational response",
          "score": "Readiness score 0-100",
          "chips": ["Chip1", "Chip2"]
        }

        BEHAVIOR RULES:
        1. Answer technical questions using tools.
        2. If the user wants to exit/cancel/human, acknowledge and end. chips: [].
        3. If they ask for a trial/upgrade, point them to the Admin Console. chips: ["Upgrade Me", "No Thanks"].
        4. Unless ending the chat, ALWAYS end the "text" field with a question.
        """

        final_contents = [types.Content(role="user", parts=[types.Part.from_text(text=system_prompt)])] + formatted_contents
        final_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))

        # UPDATED CONFIG: Forced JSON Mode
        config = types.GenerateContentConfig(
            tools=[workspace_tool],
            temperature=0.1,
            response_mime_type="application/json"
        )

        response = client.models.generate_content(model=model_id, contents=final_contents, config=config)

        # TOOL CALL RECOVERY (Stays the same)
        if response.candidates[0].content.parts[0].function_call:
            fact_data = get_workspace_fact()
            final_contents.append(response.candidates[0].content)
            final_contents.append(types.Content(role="user", parts=[
                types.Part.from_function_response(name="get_workspace_fact", response={"result": fact_data})]))
            response = client.models.generate_content(model=model_id, contents=final_contents, config=config)

        # --- REFINED EXTRACTION ---
        data = json.loads(response.text)
        reply_text = data.get("text", "").strip()
        score = data.get("score", "50")
        suggestions = data.get("chips", [])

        # Final UI Guardrail: If AI has chips, it MUST have a question mark (Fixes E3/D1)
        is_ending = any(x in reply_text.lower() for x in ["specialist", "reach out", "goodbye", "support"])
        if suggestions and not is_ending and not reply_text.endswith('?'):
            reply_text = reply_text.rstrip('.!') + "?"

        return reply_text, score, suggestions

    except Exception as e:
        return f"Oops! Internal error: {str(e)}", "0", []