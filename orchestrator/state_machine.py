"""
This module implements the core State Machine logic for the MÁV train booking system.

Responsibilities:
- Manages conversational states for the booking process.
- Appends and persists user messages to the session's history.
- Dispatches messages to target handlers based on current state.
- Executes NLU parser functions (parse_ticket_request, parse_confirmation, parse_offer_selection) to extract user intent.
- Writes successful/cancelled transaction log entries.
- Logs state transitions at INFO level.
- Catches unexpected handler errors, logs them at ERROR level, and resets sessions.
"""

import os
import sqlite3
import json
import logging
from datetime import datetime
from typing import Any, Dict

import orchestrator.session_store as session_store
from nlu.parser import parse_ticket_request, parse_confirmation, parse_offer_selection
from telegram.messages import (
    MSG_CANCEL,
    MSG_PAYMENT_SUCCESS,
    MSG_PAYMENT_CANCELLED,
    MSG_ERROR,
    MSG_INVALID_SELECTION,
    MSG_RESTART,
    format_ticket_summary,
    format_search_results,
    format_final_confirmation,
)

# Set up logging
logger = logging.getLogger(__name__)

# States
STATE_WAITING_FOR_REQUEST = "vár_kérésre"
STATE_WAITING_FOR_CONFIRMATION_1 = "vár_megerősítés_1"
STATE_SEARCHING = "keres"
STATE_WAITING_FOR_CONFIRMATION_2 = "vár_megerősítés_2"
STATE_PAYING = "fizet"
STATE_DONE = "kész"

def _change_state(session: dict, chat_id: int, new_state: str) -> None:
    """
    Changes the state of the session and logs the transition.
    """
    old_state = session.get("state", STATE_WAITING_FOR_REQUEST)
    session["state"] = new_state
    if old_state != new_state:
        logger.info(f"state_machine | chat_id={chat_id} | {old_state} → {new_state}")


def _get_value(val: Any) -> Any:
    """
    Extracts the raw value of an Enum, or returns the value itself.
    """
    if hasattr(val, "value"):
        return val.value
    return val


def _format_ticket_request_summary(req: Any) -> str:
    """
    Formats the TicketRequest model/dict to a human-readable Hungarian summary.
    """
    if hasattr(req, "model_dump"):
        req_dict = req.model_dump()
    else:
        req_dict = req if isinstance(req, dict) else {}
    return format_ticket_summary(req_dict)


def _handle_waiting_for_request(chat_id: int, session: dict) -> str:
    result = parse_ticket_request(session["message_history"])
    status = result.get("status")
    
    if status == "ready":
        data = result.get("data")
        if hasattr(data, "model_dump"):
            session["ticket_request"] = data.model_dump()
        else:
            session["ticket_request"] = data
            
        _change_state(session, chat_id, STATE_WAITING_FOR_CONFIRMATION_1)
        return _format_ticket_request_summary(session["ticket_request"])
        
    elif status == "needs_clarification":
        return result.get("message", "Nem sikerült értelmezni a kérést.")
        
    return "Nem sikerült értelmezni a kérést."


def _handle_waiting_for_first_confirmation(chat_id: int, session: dict) -> str:
    result = parse_confirmation(session["message_history"])
    status = result.get("status")
    
    if status == "ready":
        data = result.get("data")
        decision = getattr(data, "decision", None)
        
        if decision == "megerosit":
            _change_state(session, chat_id, STATE_SEARCHING)
            return _handle_searching(chat_id, session)
            
        elif decision == "modosit":
            fields_to_modify = getattr(data, "fields_to_modify", {}) or {}
            req = session.get("ticket_request", {})
            
            if isinstance(req, dict):
                for k, v in fields_to_modify.items():
                    req[k] = v
            else:
                for k, v in fields_to_modify.items():
                    setattr(req, k, v)
                    
            return _format_ticket_request_summary(session["ticket_request"])
            
        elif decision in ("elutasit", "megszakit"):
            session_store.delete(chat_id)
            session["_deleted"] = True
            return MSG_CANCEL
            
    elif status == "needs_clarification":
        return result.get("message", "Nem sikerült értelmezni a megerősítést.")
        
    return "Nem sikerült értelmezni a megerősítést."


def _handle_searching(chat_id: int, session: dict) -> str:
    mock_results = [
        {"train": "IC 503", "departure": "14:05", "arrival": "16:55",
         "duration": "2h 50m", "price": 3890, "class": "2. osztály"},
        {"train": "IC 701", "departure": "16:05", "arrival": "18:55",
         "duration": "2h 50m", "price": 3890, "class": "2. osztály"},
        {"train": "Személyvonat", "departure": "14:32", "arrival": "18:10",
         "duration": "3h 38m", "price": 2100, "class": "2. osztály"},
    ]
    
    session["search_results"] = mock_results
    _change_state(session, chat_id, STATE_WAITING_FOR_CONFIRMATION_2)
    
    return format_search_results(mock_results)


def _handle_waiting_for_second_confirmation(chat_id: int, session: dict) -> str:
    result = parse_offer_selection(session["message_history"])
    status = result.get("status")
    
    if status == "ready":
        data = result.get("data")
        none_suitable = getattr(data, "none_suitable", False)
        selected_index = getattr(data, "selected_index", None)
        
        if none_suitable:
            session_store.delete(chat_id)
            session["_deleted"] = True
            return MSG_RESTART
            
        if selected_index is not None:
            search_results = session.get("search_results", [])
            if not (0 <= selected_index < len(search_results)):
                return MSG_INVALID_SELECTION
                
            session["selected_offer"] = search_results[selected_index]
            _change_state(session, chat_id, STATE_PAYING)
            
            offer = session["selected_offer"]
            return format_final_confirmation(offer)
            
    elif status == "needs_clarification":
        return result.get("message", "Nem sikerült értelmezni a választást.")
        
    return "Nem sikerült értelmezni a választást."


def _handle_payment(chat_id: int, session: dict) -> str:
    result = parse_confirmation(session["message_history"])
    status = result.get("status")
    
    if status == "ready":
        data = result.get("data")
        decision = getattr(data, "decision", None)
        
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        if decision == "megerosit":
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "status": "sikeres",
                "chat_id": chat_id,
                "offer": session.get("selected_offer")
            }
            with open("logs/transactions.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                
            session_store.delete(chat_id)
            session["_deleted"] = True
            return MSG_PAYMENT_SUCCESS
            
        elif decision in ("elutasit", "megszakit"):
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "status": "megszakitva",
                "chat_id": chat_id,
                "reason": "user_cancel"
            }
            with open("logs/transactions.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                
            session_store.delete(chat_id)
            session["_deleted"] = True
            return MSG_PAYMENT_CANCELLED
            
    elif status == "needs_clarification":
        return result.get("message", "Nem sikerült értelmezni a megerősítést.")
        
    return "Nem sikerült értelmezni a megerősítést."


def handle_message(chat_id: int, user_message: str) -> str:
    """
    Main entry point for handling incoming Telegram messages.
    """
    # 1. Fetch session
    session = session_store.get(chat_id)
    
    # 2. Append user message to history
    if "message_history" not in session:
        session["message_history"] = []
    session["message_history"].append({"role": "user", "content": user_message})
    
    # 3. Save updated history
    session_store.set(chat_id, session)
    
    # 4. Route based on state
    state = session.get("state", STATE_WAITING_FOR_REQUEST)
    
    handlers = {
        STATE_WAITING_FOR_REQUEST: _handle_waiting_for_request,
        STATE_WAITING_FOR_CONFIRMATION_1: _handle_waiting_for_first_confirmation,
        STATE_SEARCHING: _handle_searching,
        STATE_WAITING_FOR_CONFIRMATION_2: _handle_waiting_for_second_confirmation,
        STATE_PAYING: _handle_payment,
    }
    
    if state not in handlers:
        logger.error(f"state_machine | chat_id={chat_id} | Unexpected state: {state}")
        try:
            session_store.delete(chat_id)
        except Exception:
            pass
        return MSG_ERROR
        
    try:
        response_text = handlers[state](chat_id, session)
        
        # 5. Save the updated session if it wasn't deleted
        if not session.get("_deleted", False):
            session_store.set(chat_id, session)
            
        return response_text
        
    except PermissionError:
        raise
    except Exception as e:
        logger.error(f"state_machine | chat_id={chat_id} | Unexpected error in state '{state}': {e}", exc_info=True)
        try:
            session_store.delete(chat_id)
        except Exception:
            pass
        return MSG_ERROR
