import os
from dotenv import load_dotenv
 
from openai import OpenAI
 
def build_messages(user_text: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "You are a very helpful assistant. "
                "Be concise, correct, and do not invent facts. "
                "If unsure, say you are unsure."
            ),
        },
        {"role": "user", "content": user_text},
    ]
 
def call_llm(client: OpenAI, user_text: str) -> str:
    messages = build_messages(user_text)
 
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2,
        max_tokens=300,
    )
 
    return resp.choices[0].message.content.strip()
 
def main():
    load_dotenv()
 
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY. Put it in a .env file.")
 
    client = OpenAI(api_key=api_key)
 
    print("CLI AI Assistant (type 'exit' to quit)")
    while True:
        user_text = input("\nYou: ").strip()
        if user_text.lower() in {"exit", "quit"}:
            print("Goodbye")
            break
        if not user_text:
            print("Please enter a question.")
            continue
 
        try:
            answer = call_llm(client, user_text)
            print("\nAssistant:", answer)
        except Exception as e:
            print("\nError calling the LLM API:", str(e))
 
if __name__ == "__main__":
    main()