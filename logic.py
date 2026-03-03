"""
File: logic.py
Description: Backend logic for Workspace Sales Agent using Structured JSON Output.
Final Polish: Fixes NoneType tool recovery and improves chip relevance.
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
        Target: Business Standard ($12/user/month).
        
        OUTPUT FORMAT (JSON ONLY):
        {
          "text": "Conversational response ending in a question",
          "score": "0-100",
          "chips": ["Topic A", "Topic B"]
        }

        STRICT RULES:
        1. You ARE the expert. Never ask 'What is Meet Premium?'—use your tools or your knowledge to answer.
        2. Chips must be HIGHLY SPECIFIC to the user's last question (e.g., if asking about Outlook, chips should be about 'Syncing' or 'Calendar').
        3. If the user is ready (trial, sign up, upgrade), use chips: ["Upgrade Me", "No Thanks"].
        4. If the conversation is ending, use chips: [].
        """

        final_contents = [types.Content(role="user", parts=[types.Part.from_text(text=system_prompt)])] + formatted_contents
        final_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))

        config = types.GenerateContentConfig(
            tools=[workspace_tool],
            temperature=0.1,
            response_mime_type="application/json"
        )

        response = client.models.generate_content(model=model_id, contents=final_contents, config=config)

        # TOOL CALL RECOVERY with NoneType Safety (Fixes E2)
        if response.candidates and response.candidates[0].content.parts[0].function_call:
            fact_data = get_workspace_fact()
            final_contents.append(response.candidates[0].content)
            final_contents.append(types.Content(role="user", parts=[
                types.Part.from_function_response(name="get_workspace_fact", response={"result": fact_data})]))
            response = client.models.generate_content(model=model_id, contents=final_contents, config=config)

        # --- SAFE PARSING ---
        if not response.text:
            raise ValueError("Empty response from model")

        data = json.loads(response.text)
        reply_text = data.get("text", "").strip()
        score = data.get("score", "50")
        suggestions = data.get("chips", [])

        # Final Question Mark Enforcement
        is_ending = any(x in reply_text.lower() for x in ["goodbye", "reach out", "support", "sorry i can't"])
        if suggestions and not is_ending and not reply_text.endswith('?'):
            reply_text = reply_text.rstrip('.!') + "?"

        return reply_text, score, suggestions

    except Exception as e:
        return f"I'm having a bit of trouble connecting to my resources. Could you try rephrasing that?", "0", []