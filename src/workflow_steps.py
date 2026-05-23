import os
import json
import time
from typing import Dict, Any
from dotenv import load_dotenv
from groq import Groq
 
MODEL = "llama-3.3-70b-versatile"
 
 
def step1_load_input(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    return {"ok": True, "input_path": file_path, "raw_text": text}
 
 
def step2_extract_structured(raw_text: str) -> Dict[str, Any]:
    """
    Extract structured fields from raw text safely.
    Removes markdown code blocks and handles parsing failures gracefully.
    """
    load_dotenv()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
 
    system = (
        "Extract structured information from the user text.\n"
        "Return ONLY raw, valid JSON text. Do NOT use markdown code blocks or ``` tags.\n"
        "Required keys:\n"
        "topic, requester, urgency (low|medium|high), summary, action_items (array of strings).\n"
        "If unknown, use null or empty values.\n"
    )
 
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": raw_text},
            ],
            temperature=0.0,
            max_tokens=500,
        )
     
        content = (resp.choices[0].message.content or "").strip()
        
        # --- Clean Markdown Code Blocks if LLM ignored instructions ---
        if content.startswith("```json"):
            content = content.replace("```json", "", 1)
        elif content.startswith("```"):
            content = content.replace("```", "", 1)
            
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
            
        content = content.strip()
     
        # --- Safe JSON Parsing ---
        data = json.loads(content)
        
    except json.JSONDecodeError as je:
        return {
            "ok": False, 
            "error": f"JSON syntax error from AI: {str(je)}", 
            "raw": content if 'content' in locals() else "No response generated"
        }
    except Exception as e:
        return {"ok": False, "error": f"API or system failure: {str(e)}"}
 
    # Validate keys
    required = {"topic", "requester", "urgency", "summary", "action_items"}
    missing = required - set(data.keys())
    if missing:
        return {"ok": False, "error": f"Missing keys: {sorted(list(missing))}", "raw": content}
 
    return {"ok": True, "extracted": data}
 
 
def step3_classify_and_route(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic routing rules based on urgency.
    """
    urgency = (extracted.get("urgency") or "").lower()
    if urgency not in {"low", "medium", "high"}:
        urgency = "medium"
 
    if urgency == "high":
        route = "priority"
        sla = "4 hours"
    elif urgency == "medium":
        route = "standard"
        sla = "24 hours"
    else:
        route = "low"
        sla = "72 hours"
 
    return {"ok": True, "route": route, "sla": sla}
 
 
def step4_generate_draft_reply(extracted: Dict[str, Any], route: str, sla: str) -> Dict[str, Any]:
    """
    Generate a user-facing draft reply grounded in extracted fields.
    """
    load_dotenv()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
 
    system = (
        "Write a concise, professional response draft.\n"
        "Use only the provided structured fields.\n"
        "If information is missing, ask one clarifying question.\n"
    )
 
    user = {
        "route": route,
        "sla": sla,
        "extracted": extracted,
    }
 
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)},
        ],
        temperature=0.2,
        max_tokens=550,
    )
 
    draft = (resp.choices[0].message.content or "").strip()
    return {"ok": True, "draft_reply": draft}
 
 
def step5_save_outputs(out_base: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    os.makedirs(out_base, exist_ok=True)
 
    # Save JSON
    json_path = os.path.join(out_base, "result.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
 
    # Save draft reply
    draft_path = os.path.join(out_base, "draft_reply.txt")
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(payload.get("draft_reply", ""))
 
    return {"ok": True, "json_path": json_path, "draft_path": draft_path}
 
 
def step6_log_run(log_path: str, record: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    record = dict(record)
    record["ts"] = int(time.time())
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")