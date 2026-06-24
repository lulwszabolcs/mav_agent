"""
This module manages the persistent storage of chat sessions in an SQLite database, keyed by chat_id.

Key Responsibilities:
- Persistent SQLite storage in 'data/sessions.db'.
- Basic CRUD operations (get, set, delete) for session data.
- Automatically handles serialization and deserialization of JSON fields and Pydantic models (like TicketRequest).
- Validates every request against a whitelist of ALLOWED_CHAT_IDS (loaded from .env).
- Automated update timestamp tracking (updated_at).
- INFO logging on method execution without logging sensitive user details.
"""

import os
import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

# Setup logger
logger = logging.getLogger(__name__)

# Parse ALLOWED_CHAT_IDS constant
allowed_raw = os.environ.get("ALLOWED_CHAT_IDS", "")
ALLOWED_CHAT_IDS = []
if allowed_raw:
    for cid in allowed_raw.split(","):
        cid = cid.strip()
        if cid.isdigit() or (cid.startswith("-") and cid[1:].isdigit()):
            ALLOWED_CHAT_IDS.append(int(cid))

DB_PATH = "data/sessions.db"

# Try to import TicketRequest for parsing back from database
try:
    from nlu.schema import TicketRequest
except ImportError:
    TicketRequest = None


def _init_db() -> None:
    """
    Initializes the SQLite database. Creates the data directory and the sessions table if they do not exist.
    """
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    chat_id INTEGER PRIMARY KEY,
                    state TEXT NOT NULL,
                    ticket_request TEXT,
                    search_results TEXT,
                    selected_offer TEXT,
                    message_history TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)
    finally:
        conn.close()


def _validate_chat_id(chat_id: Any) -> int:
    """
    Validates if the given chat_id is in the ALLOWED_CHAT_IDS.
    Raises PermissionError if not.
    """
    try:
        cid = int(chat_id)
    except (ValueError, TypeError):
        raise PermissionError(f"Access denied. Invalid chat_id format: {chat_id}")
    
    if cid not in ALLOWED_CHAT_IDS:
        raise PermissionError(f"Access denied for chat_id: {chat_id}. Chat ID is not allowed.")
    
    return cid


def _to_json_compatible(obj: Any) -> Any:
    """
    Recursively converts non-serializable objects (like Pydantic models) to serializable dicts/lists.
    """
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {k: _to_json_compatible(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_compatible(item) for item in obj]
    return obj


def get(chat_id: Any) -> dict:
    """
    Retrieves the session data for the specified chat_id.
    If the chat_id does not exist, returns a default session.
    """
    logger.info(f"session_store | get | chat_id={chat_id}")
    cid = _validate_chat_id(chat_id)
    
    _init_db()
    
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT state, ticket_request, search_results, selected_offer, message_history, updated_at
            FROM sessions WHERE chat_id = ?
        """, (cid,))
        row = cursor.fetchone()
    finally:
        conn.close()
        
    if row is None:
        return {
            "chat_id": cid,
            "state": "vár_kérésre",
            "ticket_request": None,
            "search_results": None,
            "selected_offer": None,
            "message_history": [],
            "updated_at": None
        }
        
    state, ticket_request_json, search_results_json, selected_offer_json, message_history_json, updated_at = row
    
    ticket_request = None
    if ticket_request_json is not None:
        try:
            ticket_request_dict = json.loads(ticket_request_json)
            if ticket_request_dict is not None and TicketRequest is not None:
                ticket_request = TicketRequest(**ticket_request_dict)
            else:
                ticket_request = ticket_request_dict
        except Exception:
            ticket_request = None
            
    search_results = json.loads(search_results_json) if search_results_json is not None else None
    selected_offer = json.loads(selected_offer_json) if selected_offer_json is not None else None
    
    try:
        message_history = json.loads(message_history_json)
    except Exception:
        message_history = []
        
    return {
        "chat_id": cid,
        "state": state,
        "ticket_request": ticket_request,
        "search_results": search_results,
        "selected_offer": selected_offer,
        "message_history": message_history,
        "updated_at": updated_at
    }


def set(chat_id: Any, session: dict) -> None:
    """
    Saves or overrides the session data for the specified chat_id.
    Automatically serializes Pydantic models to JSON and updates the updated_at timestamp.
    """
    logger.info(f"session_store | set | chat_id={chat_id}")
    cid = _validate_chat_id(chat_id)
    
    _init_db()
    
    state = session.get("state", "vár_kérésre")
    ticket_request = session.get("ticket_request")
    search_results = session.get("search_results")
    selected_offer = session.get("selected_offer")
    message_history = session.get("message_history", [])
    
    # Handle serialization
    ticket_request_json = None
    if ticket_request is not None:
        ticket_request_json = json.dumps(_to_json_compatible(ticket_request))
        
    search_results_json = None
    if search_results is not None:
        search_results_json = json.dumps(_to_json_compatible(search_results))
        
    selected_offer_json = None
    if selected_offer is not None:
        selected_offer_json = json.dumps(_to_json_compatible(selected_offer))
        
    message_history_json = json.dumps(_to_json_compatible(message_history))
    
    updated_at = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (chat_id, state, ticket_request, search_results, selected_offer, message_history, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cid, state, ticket_request_json, search_results_json, selected_offer_json, message_history_json, updated_at))
    finally:
        conn.close()


def delete(chat_id: Any) -> None:
    """
    Deletes the session data for the specified chat_id.
    This operation is silent if the chat_id does not exist.
    """
    logger.info(f"session_store | delete | chat_id={chat_id}")
    cid = _validate_chat_id(chat_id)
    
    _init_db()
    
    conn = sqlite3.connect(DB_PATH)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE chat_id = ?", (cid,))
    finally:
        conn.close()
