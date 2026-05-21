import os
import json
import time
from typing import Dict, List, Any
 
SESSIONS_PATH = "data/sessions.json"
 
# In-memory cache: session_id -> session dict
_sessions: Dict[str, Dict[str, Any]] = {}
 
 
def load_sessions_from_disk() -> None:
    global _sessions
    if not os.path.exists(SESSIONS_PATH):
        _sessions = {}
        return
    with open(SESSIONS_PATH, "r", encoding="utf-8") as f:
        _sessions = json.load(f)
 
 
def save_sessions_to_disk() -> None:
    os.makedirs(os.path.dirname(SESSIONS_PATH), exist_ok=True)
    with open(SESSIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(_sessions, f, ensure_ascii=False, indent=2)
 
 
def get_or_create_session(session_id: str) -> Dict[str, Any]:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "session_id": session_id,
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
            "messages": []  # list of {"role": "user"|"assistant", "content": str, "ts": int}
        }
    return _sessions[session_id]
 
 
def append_message(session_id: str, role: str, content: str) -> None:
    sess = get_or_create_session(session_id)
    sess["messages"].append({"role": role, "content": content, "ts": int(time.time())})
    sess["updated_at"] = int(time.time())
 
 
def get_recent_messages(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    sess = get_or_create_session(session_id)
    return sess["messages"][-limit:]
 
 
def cleanup_sessions(max_age_seconds: int = 60 * 60 * 24 * 7) -> int:
    """
    Remove sessions older than max_age_seconds since last update.
    Returns number removed.
    """
    now = int(time.time())
    to_delete = []
    for sid, sess in _sessions.items():
        if now - int(sess.get("updated_at", now)) > max_age_seconds:
            to_delete.append(sid)
    for sid in to_delete:
        del _sessions[sid]
    return len(to_delete)