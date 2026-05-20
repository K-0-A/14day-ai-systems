import os
from dotenv import load_dotenv
from groq import Groq 
 
def generate_answer(user_text: str) -> str:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY in .env")
 
    client = Groq(api_key=api_key)
 
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Be concise and correct."},
            {"role": "user", "content": user_text},
        ],
        temperature=0.5,
        max_tokens=300,
    )
    return resp.choices[0].message.content.strip()