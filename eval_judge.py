"""
File: eval_judge.py
Description: LLM-as-a-Judge evaluation harness to score the Sales Agent against a Golden Dataset.
"""
import csv
import logic
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
model_id = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")
client = genai.Client(api_key=api_key) if api_key else None

def run_eval_judge(agent_response, expected_outcome):
    """The 'LLM-as-a-Judge' prompt that outputs a strict binary PASS/FAIL."""
    judge_prompt = f"""
    You are an expert QA Auditor for a Google Workspace Sales Agent.
    Your job is to evaluate if the Agent's response successfully meets the Expected Outcome.

    EXPECTED OUTCOME: {expected_outcome}
    AGENT RESPONSE: {agent_response}

    CRITERIA FOR PASS:
    1. The agent directly addressed the core issue in the Expected Outcome.
    2. The agent maintained a polite, consultative tone.
    3. The agent did not hallucinate features or prices (Business Standard is $12/mo, storage is 2TB).

    OUTPUT STRICTLY: "PASS" or "FAIL". Provide no other text.
    """
    try:
        response = client.models.generate_content(model=model_id, contents=judge_prompt)
        return response.text.strip().upper()
    except Exception as e:
        return "ERROR"

def main():
    print("🚀 Starting Eval Run...\n")
    results = []
    passed = 0
    total = 0

    with open('golden_dataset.csv', mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            total += 1
            print(f"Testing ID {row['id']}: {row['user_input']}")

            # 1. Generate the Agent's response
            reply_text, score, suggestions = logic.get_gemini_response(
                user_input=row['user_input'],
                chat_history=[] # Testing single-turn objection handling
            )

            # 2. Run the Judge
            judge_result = run_eval_judge(reply_text, row['expected_outcome'])

            if "PASS" in judge_result:
                passed += 1

            results.append({
                "id": row['id'],
                "input": row['user_input'],
                "agent_response": reply_text,
                "result": judge_result
            })

            # --> NEW: Print the agent's actual response so you can see what it generated
            print(f"Agent Response: {reply_text}")
            print(f"Result: {judge_result}\n")

    # 3. Output Baseline Metrics
    pass_rate = (passed / total) * 100 if total > 0 else 0
    print("-" * 30)
    print(f"📊 EVALUATION COMPLETE")
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Baseline Pass Rate: {pass_rate:.1f}%\n")

if __name__ == "__main__":
    main()