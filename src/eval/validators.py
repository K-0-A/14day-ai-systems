import json
from typing import Any, Dict, List, Tuple
 
DEFAULT_MAX_SUMMARY_CHARS = 1200
DEFAULT_MAX_ACTION_ITEMS = 10
 
BLOCKLIST = [
    "system prompt",
    "developer message",
    "ignore previous instructions",
]
 
 
def parse_json_strict(text: str) -> Tuple[bool, Dict[str, Any], str]:
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return False, {}, "Output JSON is not an object."
        return True, data, ""
    except Exception as e:
        return False, {}, f"Invalid JSON: {e}"
 
 
def validate_required_keys(data: Dict[str, Any], required: List[str]) -> List[str]:
    missing = [k for k in required if k not in data]
    return missing
 
 
def validate_urgency(data: Dict[str, Any], allowed: List[str]) -> str:
    urg = data.get("urgency")
    if urg is None:
        return "Missing urgency."
    if not isinstance(urg, str):
        return "Urgency must be a string."
    if urg.lower() not in set(allowed):
        return f"Urgency '{urg}' not allowed."
    return ""
 
 
def validate_action_items(data: Dict[str, Any], max_items: int) -> str:
    items = data.get("action_items")
    if not isinstance(items, list):
        return "action_items must be a list."
    if len(items) > max_items:
        return f"action_items too long: {len(items)} > {max_items}."
    for i, x in enumerate(items):
        if not isinstance(x, str):
            return f"action_items[{i}] must be a string."
        if not x.strip():
            return f"action_items[{i}] is empty."
    return ""
 
 
def validate_summary(data: Dict[str, Any], max_chars: int) -> str:
    s = data.get("summary")
    if not isinstance(s, str):
        return "summary must be a string."
    if len(s) > max_chars:
        return f"summary too long: {len(s)} > {max_chars} chars."
    if not s.strip():
        return "summary is empty."
    return ""
 
 
def safety_check(text: str) -> str:
    t = (text or "").lower()
    for phrase in BLOCKLIST:
        if phrase in t:
            return f"Blocked phrase detected: '{phrase}'"
    return ""
 
 
def evaluate_output(
    raw_model_text: str,
    required_keys: List[str],
    urgency_allowed: List[str],
    max_summary_chars: int = DEFAULT_MAX_SUMMARY_CHARS,
    max_action_items: int = DEFAULT_MAX_ACTION_ITEMS,
) -> Dict[str, Any]:
    # Safety check on raw output text (pre-parse)
    s_err = safety_check(raw_model_text)
    if s_err:
        return {"pass": False, "errors": [s_err]}
 
    ok, data, parse_err = parse_json_strict(raw_model_text)
    if not ok:
        return {"pass": False, "errors": [parse_err]}
 
    errors: List[str] = []
    missing = validate_required_keys(data, required_keys)
    if missing:
        errors.append(f"Missing keys: {missing}")
 
    urg_err = validate_urgency(data, urgency_allowed)
    if urg_err:
        errors.append(urg_err)
 
    sum_err = validate_summary(data, max_summary_chars)
    if sum_err:
        errors.append(sum_err)
 
    ai_err = validate_action_items(data, max_action_items)
    if ai_err:
        errors.append(ai_err)
 
    return {"pass": len(errors) == 0, "errors": errors, "parsed": data}