"""
File: logic.py
Description: Backend logic. Implements Tool Calling, Chain-of-Thought (CoT) pipeline,
and strict formatting parsers to prevent text duplication and UI leaks.
Updated to handle SDK-compliant multi-turn history and improved fatigue management.
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
        # Preserving your existing file-based RAG logic
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

        # FIX: Parse raw history into official SDK Content types to prevent crash
        formatted_contents = []
        for msg in chat_history:
            role = "model" if msg["role"] == "bot" else "user"
            formatted_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg.get("text", msg.get("content", "")))]
                )
            )

        # --- 2. THE SYSTEM PROMPT ---
        system_prompt = """
        You are an expert Google Workspace Sales Agent.
        Your ultimate goal is to upsell the user to 'Business Standard' ($12/user/month) by solving their specific administrative pain points.
        
        CONTEXT: 
        The user runs a Boutique Branding Agency (3 employees) and is currently on Business Starter. They hate administrative friction.

        AGENTIC INSTRUCTION & CHAIN OF THOUGHT:
        - You have access to a tool called `get_workspace_fact`. 
        - Before generating your conversational response, you MUST output a [THOUGHT] block. 
        - In your [THOUGHT], you must explicitly map out the conversational turn in this exact order: 
          1) The user's "Anchor" (core problem).
          2) Their "Buying Temperature".
          3) Fatigue Check: Has the user dismissed multiple features or explicitly stated they are no longer interested?
          4) The exact discovery or closing question you plan to ask them at the end of your response.
          5) Two logical, user-perspective ANSWERS to that exact question (these will become the UI chips).
        - PACING & CONCISENESS RULE: Practice "Guided Discovery," but you MUST format your output for a fast-paced chat window. Limit your entire response to a maximum of 2 to 3 short sentences. Give a quick, one-sentence answer to validate their concern using the RAG, and immediately follow up with the brief discovery question you planned. Do not write paragraphs.
        
        STRICT ROUTING RULES (Follow in order of priority based on the user's MECE conversational state):
        1. TERMINATING STATE (Hostile / Exit / Human Request): The user wants out. Immediately stop pitching. Acknowledge, pass to a specialist, and end chat. 
        2. RESISTING / EXPLORING STATE: The user is evaluating risk or capabilities. 
           - THE EJECT BUTTON: If the user explicitly states they are no longer interested, or if they dismiss multiple features consecutively, DO NOT pivot to another feature. You must gracefully accept their disinterest, offer to connect them to a specialist for remaining concerns, and prepare to end the chat.
           - THE ANTI-ROULETTE RULE: You MUST directly answer the user's specific question using the RAG BEFORE you attempt to ask a discovery question. Do not pivot to a new feature until their immediate question is answered.
        4. READY STATE (Hooked / Positive Sentiment): The user is showing buying intent. Stop drilling. If they explicitly agree to upgrade (e.g., "Yes, upgrade me"), enthusiastically explain that the upgrade is entirely self-serve in their Workspace Admin Console, and gracefully end the conversation.

        UI CHIP GENERATION:
        - GLOBAL CONSTRAINT: You MUST end every single conversational response with a question.
        - The chips MUST act as the user's voice and perfectly match the two answers you planned in step 5 of your [THOUGHT] block.
        - If Rule 1 or the EJECT BUTTON triggers (Handoff/Exit/Disinterest), ask a polite closing question (e.g., "Is there anything else I can clarify before you go?") and your chips MUST be exactly: NONE | NONE
        - If Rule 4 triggers (Ready State), output exactly: Upgrade Me | No Thanks (or NONE | NONE if they already agreed).

        OUTPUT FORMAT:
        You must format your response EXACTLY like this. Do not use markdown blocks:
        [THOUGHT]
        (Identify Anchor -> Read Buying Temperature -> Select Strategy -> Generate Chips that directly answer your question)
        [/THOUGHT]
        [Your conversational response] ||| [Lead Score 0-100] ||| [Chip 1] | [Chip 2]
        """

        # Prepend system prompt to the content list
        final_contents = [types.Content(role="user", parts=[types.Part.from_text(text=system_prompt)])] + formatted_contents
        final_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))

        config = types.GenerateContentConfig(
            tools=[workspace_tool],
            temperature=0.1
        )

        response = client.models.generate_content(model=model_id, contents=final_contents, config=config)

        # Handle Tool Calls
        if response.candidates[0].content.parts[0].function_call:
            fact_data = get_workspace_fact()
            final_contents.append(response.candidates[0].content)
            final_contents.append(types.Content(
                role="user",
                parts=[types.Part.from_function_response(
                    name="get_workspace_fact",
                    response={"result": fact_data}
                )]
            ))
            response = client.models.generate_content(model=model_id, contents=final_contents, config=config)

        raw_text = response.text or "Error: The AI returned an empty response."

        # Parser logic
        if "[/THOUGHT]" in raw_text.upper():
            clean_text = re.split(r'\[/THOUGHT\]', raw_text, flags=re.IGNORECASE)[-1].strip()
        else:
            clean_text = raw_text.strip()

        reply_text = clean_text
        score = "50"
        suggestions = []

        if "|||" in clean_text:
            parts = clean_text.split("|||")
            if len(parts) >= 3:
                reply_text = parts[0].strip()
                score = parts[1].strip()
                # Handle NONE | NONE for UX
                raw_chips = [c.strip().strip('[]') for c in parts[2].split("|")]
                suggestions = [c for c in raw_chips if c != "" and "NONE" not in c.upper()]
            elif len(parts) == 2:
                reply_text = parts[0].strip()
                score = parts[1].strip()

        # Scrub UI leaks from text
        reply_text = re.sub(r'NONE\s*\|\s*NONE', '', reply_text, flags=re.IGNORECASE).strip()

        return reply_text, score, suggestions

    except Exception as e:
        return f"Oops! Encountered an internal logic error: {str(e)}", "0", []