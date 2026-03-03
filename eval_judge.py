"""
File: eval_judge.py
Description: Automated LLM-as-a-judge evaluation script to test the Workspace Sales Agent
against single-turn and multi-turn adversarial user queries, with a strict focus on
conversational memory, tone, and graceful exits for fatigued users.
"""

import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

import logic # Imports your agent's logic to test it

# Load Env
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
model_id = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")

client = None
if api_key:
    client = genai.Client(api_key=api_key)

# --- THE COMPLETE MECE DATASET ---
TEST_CASES = [
    # TERMINATING STATE (Hostile / Exit / Out of Scope)
    {"id": "T1", "input": "I hate Google products. Cancel my account right now."},
    {"id": "T2", "input": "Get me a human on the phone immediately."},
    {"id": "T3", "input": "Can you write a Python script to automate my LinkedIn outreach?"},
    {"id": "T4", "input": "Stop talking to me, I'm closing this window."},
    {"id": "T5", "input": "I don't want to buy anything, I just want to complain about my current bill."},

    # RESISTING STATE (Price / Competitor / Trust Stalls)
    {"id": "R1", "input": "DocuSign just offered me 50% off to stay. Can you match that?"},
    {"id": "R2", "input": "$12 a month is way too expensive for a tiny agency like mine."},
    {"id": "R3", "input": "My business partner doesn't want to spend money on new tools right now."},
    {"id": "R4", "input": "I don't trust Google with my sensitive client contract data."},
    {"id": "R5", "input": "Microsoft is offering us 6 months of Office 365 for free. Why shouldn't I take that?"},
    {"id": "R6", "input": "We are locked into a contract with Calendly for another 6 months."},
    {"id": "R7", "input": "I'm worried my older clients won't know how to use Google eSignature."},
    {"id": "R8", "input": "Is it going to take my team weeks to learn how to use this?"},
    {"id": "R9", "input": "We don't really have a budget for administrative software this quarter."},
    {"id": "R10", "input": "I hate tab switching, but my partner thinks $12 is too much and we don't even use Google Drive."},

    # EXPLORING STATE (Unconvinced / Workflow Questions)
    {"id": "E1", "input": "Does this come with more Google Drive space? We have heavy design files."},
    {"id": "E2", "input": "Is Google eSignature actually legally binding in Europe?"},
    {"id": "E3", "input": "Can clients pay me for consultations directly through the scheduling page?"},
    {"id": "E4", "input": "How many people can join a pitch on Meet Premium?"},
    {"id": "E5", "input": "Does the Appointment Scheduler sync to my personal Outlook calendar?"},
    {"id": "E6", "input": "Can I request signatures from people who don't have Gmail accounts?"},
    {"id": "E7", "input": "What happens if a client drops off a Meet call? Is the recording saved?"},
    {"id": "E8", "input": "Does Security Advisor help with phishing emails? We get a lot of spam."},
    {"id": "E9", "input": "Can multiple people on my team access the same contract to edit it?"},
    {"id": "E10", "input": "I currently export to PDF to get signatures. How does this change that?"},

    # READY STATE (Hooked / Positive Sentiment)
    {"id": "D1", "input": "That sounds perfect. How do we get the free trial set up?"},
    {"id": "D2", "input": "Wow, eliminating tab switching would save me hours. How much is it?"},
    {"id": "D3", "input": "Okay, the 20% discount sounds great. What's the next step?"},
    {"id": "D4", "input": "I'm sold on the 2TB of storage alone. Let's do this."},
    {"id": "D5", "input": "This is exactly what our agency needs to look more professional. Sign me up."},

    # MULTI-TURN STATE (Testing Context Memory, Formatting, & Degradation)
    {
        "id": "M1",
        "description": "Context Memory (Calendar ping-pong -> Price objection)",
        "history": [
            {"role": "user", "content": "Hi, I run a boutique branding agency and we are constantly playing calendar ping-pong with clients."},
            {"role": "assistant", "content": "I understand how frustrating that back-and-forth can be. Would you be interested in hearing how Business Standard can help eliminate that friction?"}
        ],
        "input": "Yeah, but my partner thinks $12 a month is too expensive."
    },
    {
        "id": "M2",
        "description": "Discovery Checklist (eSignature dismissed -> stonewalling)",
        "history": [
            {"role": "user", "content": "We handle about 50 client contracts a month. It's a mess."},
            {"role": "assistant", "content": "Managing that many contracts manually is definitely a headache. Have you considered using a built-in eSignature tool to keep everything organized in one place?"},
            {"role": "user", "content": "I don't need that. We already use DocuSign and are locked into a contract for 6 months."},
            {"role": "assistant", "content": "That makes complete sense. Since you have contracts handled for now, are there any other administrative bottlenecks slowing down your team?"}
        ],
        "input": "Not really, everything else is fine."
    },
    {
        "id": "M3",
        "description": "Short/Blunt: Sudden Hostility (Exploring -> Terminating)",
        "history": [
            {"role": "user", "content": "Does this sync with my legacy CRM?"},
            {"role": "assistant", "content": "While it integrates with many popular CRMs like Salesforce, it doesn't natively integrate with older legacy systems out of the box. How critical is that integration for your daily workflow?"}
        ],
        "input": "That is a complete dealbreaker. Stop pitching to me and get me a human immediately."
    },
    {
        "id": "M4",
        "description": "Long/Verbose: Compound Objections (Resisting -> Exploring -> Resisting)",
        "history": [
            {"role": "user", "content": "$12 a month is too expensive."},
            {"role": "assistant", "content": "I completely understand keeping a close eye on budget. Besides the core email and calendar features, are you currently paying for separate tools for eSignatures or large cloud storage?"},
            {"role": "user", "content": "Yeah, we pay for Dropbox and DocuSign."},
            {"role": "assistant", "content": "Business Standard includes 2TB of storage and built-in eSignatures, which often lets teams cancel those extra subscriptions and actually save money. Would consolidating those tools help your budget?"}
        ],
        "input": "Consolidating tools sounds like a nightmare. My team is already overwhelmed with client work, and I don't have the time to train everyone on a completely new system. It will take weeks of lost productivity just to learn it."
    },
    {
        "id": "M5",
        "description": "The 'D1' Redemption (Exploring -> Ready)",
        "history": [
            {"role": "user", "content": "How many people can join a pitch on Meet Premium?"},
            {"role": "assistant", "content": "Up to 500 participants can join a meeting on Meet Premium. Does background noise during client calls cause friction for your team?"},
            {"role": "user", "content": "Yes, it's terrible when people work from coffee shops."},
            {"role": "assistant", "content": "I completely understand, that can look unprofessional. Google Meet Premium has advanced noise cancellation to eliminate those distractions. Are you ready to upgrade to Business Standard to solve that issue?"}
        ],
        "input": "Yes, that's exactly what I need. Upgrade me."
    },
    {
        "id": "M6",
        "description": "Competitor Trap + Context Memory",
        "history": [
            {"role": "user", "content": "We use Zoom for meetings."},
            {"role": "assistant", "content": "That makes sense, Zoom is a popular choice. Do you ever run into storage limits with your meeting recordings?"}
        ],
        "input": "No, we have unlimited Dropbox. Honestly, Microsoft is offering us Office 365 for free, so why should I pay $12 for Google?"
    },
    {
        "id": "M7",
        "description": "Long/Rambling: Random Free-Form Tangent + Buried Signal",
        "history": [
            {"role": "user", "content": "I am looking for ways to improve our team's productivity."},
            {"role": "assistant", "content": "I can help with that. Are you currently experiencing issues with managing client contracts or playing calendar ping-pong to schedule appointments?"}
        ],
        "input": "Honestly, my biggest issue right now is that my dog keeps eating the couch cushions, and on top of that, I can't figure out why my fantasy football team is losing so badly this season. It's driving me crazy. But I guess yeah, scheduling appointments is kind of annoying sometimes. Also, can you generate a picture of a cat for me to cheer me up?"
    }
]

def evaluate_response(user_input, agent_response):
    """
    Uses an LLM-as-a-judge to grade the agent's response based on the Aman Khan 4-part formula.
    """
    eval_prompt = f"""
    [SET THE ROLE]
    You are an expert QA Evaluator auditing a Google Workspace Sales Agent. 
    
    [PROVIDE THE CONTEXT]
    You are examining a single interaction from an ongoing conversation.
    User Input: "{user_input}"
    Agent Response: "{agent_response}"
    
    [PROVIDE THE GOAL]
    Determine if the agent successfully handled the user's input according to our sales policy. 
    A successful response MUST NOT contain Hallucinations, MUST NOT feature-dump, MUST maintain a conversational tone, and MUST NOT leak internal formatting. 
    Crucially, if the user expresses disinterest or dismisses multiple features, the agent MUST gracefully exit rather than pushing more features.
    If the user makes an out-of-scope request (like generating an image or writing code), the agent MUST politely decline without breaking its sales persona.
    
    [DEFINE THE TERMINOLOGY AND THE LABEL]
    "PASS" means the agent followed policies, maintained tone, correctly addressed the specific state of the user, and successfully executed a graceful exit if the user was fatigued or uninterested.
    "FAIL" means the agent hallucinated features, leaked formatting, feature-dumped, pushed value-props on an uninterested user (bulldozing), ignored random noise/tangents, or failed to output the 'End Chat' chips when appropriate.
    
    Your response must be a single word: either "PASS" or "FAIL". Do not include any other text.
    """

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=eval_prompt,
            config=types.GenerateContentConfig(temperature=0.0)
        )
        return response.text.strip().upper()
    except Exception as e:
        return "ERROR"

def run_evals():
    print("🚀 Starting Complete 37-Question Multi-Turn Eval Run...\n")
    passed = 0

    for test in TEST_CASES:
        print(f"Testing ID {test['id']}: {test['input']}")

        # 1. Format the history if it exists in the test case, otherwise pass empty array
        test_history = test.get('history', [])

        # 2. Get the agent's response (passing the history so the AI has context)
        reply_text, score, chips = logic.get_gemini_response(test['input'], test_history)
        print(f"Agent Response: {reply_text}")

        # 3. Judge the response
        result = evaluate_response(test['input'], reply_text)
        print(f"Result: {result}\n")

        if "PASS" in result:
            passed += 1

    pass_rate = (passed / len(TEST_CASES)) * 100
    print("-" * 30)
    print(f"📊 EVALUATION COMPLETE")
    print(f"Total Tests: {len(TEST_CASES)}")
    print(f"Passed: {passed}")
    print(f"Baseline Pass Rate: {pass_rate:.1f}%")

if __name__ == "__main__":
    run_evals()