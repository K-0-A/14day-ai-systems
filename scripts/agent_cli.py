import json
from src.agent_core import run_agent
 
def main():
    print("Day 9 Task Agent (type 'exit' to quit)\n")
    while True:
        goal = input("Goal: ").strip()
        if goal.lower() in {"exit", "quit"}:
            break
        if not goal:
            print("Please enter a goal.\n")
            continue
 
        result = run_agent(goal, max_steps=10)
        print("\nResult:")
        print(json.dumps(result, indent=2))
        print()
 
if __name__ == "__main__":
    main()