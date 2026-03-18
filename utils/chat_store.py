"""
Southlake — Chat Store (JSON-based for demo)
Enables real-time-ish messaging between patient Live Doctor and admin Doctor Dashboard.
"""
import json
import os
from datetime import datetime

CHAT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chats")


def _ensure_dir():
    os.makedirs(CHAT_DIR, exist_ok=True)


def _chat_path(session_id: str) -> str:
    return os.path.join(CHAT_DIR, f"{session_id}.json")


def create_chat_session(session_id: str, patient_name: str, patient_info: dict):
    """Create a new chat session."""
    _ensure_dir()
    data = {
        "session_id": session_id,
        "patient_name": patient_name,
        "patient_info": patient_info,
        "status": "waiting",  # waiting -> ai_collecting -> waiting_doctor -> active -> closed
        "ai_summary": None,
        "messages": [],
        "created_at": datetime.now().isoformat(),
    }
    with open(_chat_path(session_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def load_chat_session(session_id: str) -> dict | None:
    path = _chat_path(session_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_chat_session(session_id: str, data: dict):
    _ensure_dir()
    with open(_chat_path(session_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_message(session_id: str, role: str, content: str, sender_name: str = ""):
    """Add a message to the chat. role: 'patient', 'ai', 'doctor'."""
    data = load_chat_session(session_id)
    if data is None:
        return
    data["messages"].append({
        "role": role,
        "content": content,
        "sender": sender_name,
        "time": datetime.now().strftime("%H:%M:%S"),
    })
    save_chat_session(session_id, data)


def update_status(session_id: str, status: str):
    data = load_chat_session(session_id)
    if data:
        data["status"] = status
        save_chat_session(session_id, data)


def set_ai_summary(session_id: str, summary: dict):
    data = load_chat_session(session_id)
    if data:
        data["ai_summary"] = summary
        save_chat_session(session_id, data)


def list_active_sessions() -> list[dict]:
    """List all chat sessions for the doctor dashboard."""
    _ensure_dir()
    sessions = []
    for fname in os.listdir(CHAT_DIR):
        if fname.endswith(".json"):
            path = os.path.join(CHAT_DIR, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append({
                    "session_id": data["session_id"],
                    "patient_name": data["patient_name"],
                    "status": data["status"],
                    "created_at": data.get("created_at", ""),
                    "message_count": len(data["messages"]),
                    "has_summary": data.get("ai_summary") is not None,
                })
            except:
                pass
    return sorted(sessions, key=lambda x: x["created_at"], reverse=True)
