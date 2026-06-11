import json
import sys
from src.agent_core import run_agent

def select_model():
    print("=============================================")
    print("  Select AI Engine (Multi-Provider Support)  ")
    print("=============================================")
    print("1) Llama 3.3 70B (Groq)    - High Reasoning [Rate Limited]")
    print("2) Llama 3 8B (Groq)       - Fast / Free Tier")
    print("3) Gemini 1.5 Flash (Google)- Fast / Efficient")
    print("4) Claude 4.6 Sonnet (Claude) - Latest SOTA (2026)")
    print("5) GPT-4o-Mini (OpenAI)    - Standard")
    print("=============================================")
    
    choice = input("Enter choice (1-5) [Default: 2]: ").strip()
    
    if choice == "1": return "llama-3.3-70b-versatile"
    elif choice == "3": return "gemini-1.5-flash"
    elif choice == "4": return "claude-4-6-sonnet-20260217"
    elif choice == "5": return "gpt-4o-mini"
    else: return "llama3-8b-8192"

def main():
    print("Day 9 Task Agent Initialization...")
    model = select_model()
    print(f"\n[System] Active Model: {model}\n")
    
    while True:
        goal = input("Goal: ").strip()
        if goal.lower() in {"exit", "quit"}:
            break
        if not goal: continue
        
        print(f"Thinking with {model}...")
        result = run_agent(goal, model_name=model, max_steps=30)
        print(json.dumps(result, indent=2))
        print()

if __name__ == "__main__":
    main()