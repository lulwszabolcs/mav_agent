import os
import json
import logging
import pytest
from unittest.mock import patch, MagicMock

import orchestrator.session_store as session_store
import orchestrator.state_machine as state_machine
from nlu.schema import TicketRequest, Passenger, PassengerType, ConfirmationResponse, ConfirmationDecision, OfferSelection


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """
    Redirects the SQLite database to a temporary location and resets whitelisted IDs.
    """
    original_db_path = session_store.DB_PATH
    temp_db = tmp_path / "test_sessions.db"
    session_store.DB_PATH = str(temp_db)
    
    original_allowed_ids = session_store.ALLOWED_CHAT_IDS
    session_store.ALLOWED_CHAT_IDS = [123456, 987654]
    
    yield temp_db
    
    session_store.DB_PATH = original_db_path
    session_store.ALLOWED_CHAT_IDS = original_allowed_ids


@pytest.fixture(autouse=True)
def cleanup_transaction_log():
    """
    Ensures logs/transactions.jsonl is removed before/after testing if it exists.
    """
    log_file = "logs/transactions.jsonl"
    if os.path.exists(log_file):
        try:
            os.remove(log_file)
        except Exception:
            pass
    yield
    if os.path.exists(log_file):
        try:
            os.remove(log_file)
        except Exception:
            pass


def test_permission_error_propagation():
    # If chat_id is not allowed, it should raise PermissionError (no catching)
    with pytest.raises(PermissionError):
        state_machine.handle_message(999999, "Szia")


@patch("orchestrator.state_machine.parse_ticket_request")
def test_handle_waiting_for_request_ready(mock_parse):
    chat_id = 123456
    
    mock_ticket_request = TicketRequest(
        departure_station="Budapest",
        destination_station="Szeged",
        departure_time_raw="ma délután",
        passengers=[Passenger(passenger_type=PassengerType.felnott, count=1)],
        ticket_class="2",
        seat_preferences=[]
    )
    mock_parse.return_value = {"status": "ready", "data": mock_ticket_request}
    
    response = state_machine.handle_message(chat_id, "Budapestről Szegedre szeretnék menni ma délután")
    
    # Assertions
    assert "Ezt értettem:" in response
    assert "Indulás:        Budapest" in response
    assert "Érkezés:        Szeged" in response
    assert "Időpont:        ma délután" in response
    assert "Utasok:         1x felnott" in response
    assert "Osztály:        2. osztály" in response
    assert "Helyes? (igen / nem / mondd meg mit változtassak)" in response
    
    # Verify DB state has updated
    session = session_store.get(chat_id)
    assert session["state"] == state_machine.STATE_WAITING_FOR_CONFIRMATION_1
    assert session["ticket_request"].departure_station == "Budapest"
    assert session["message_history"][-2]["content"] == "Budapestről Szegedre szeretnék menni ma délután"
    assert "Ezt értettem:" in session["message_history"][-1]["content"]


@patch("orchestrator.state_machine.parse_ticket_request")
def test_handle_waiting_for_request_needs_clarification(mock_parse):
    chat_id = 123456
    mock_parse.return_value = {"status": "needs_clarification", "message": "Honnan szeretne indulni?"}
    
    response = state_machine.handle_message(chat_id, "Szeretnék egy vonatjegyet")
    
    assert response == "Honnan szeretne indulni?"
    
    session = session_store.get(chat_id)
    assert session["state"] == state_machine.STATE_WAITING_FOR_REQUEST


@patch("orchestrator.state_machine.parse_confirmation")
def test_handle_waiting_for_first_confirmation_megerosit(mock_parse):
    chat_id = 123456
    # Seed session
    session_store.set(chat_id, {
        "state": state_machine.STATE_WAITING_FOR_CONFIRMATION_1,
        "ticket_request": {"departure_station": "Budapest", "destination_station": "Szeged"},
        "message_history": []
    })
    
    mock_parse.return_value = {
        "status": "ready",
        "data": ConfirmationResponse(decision=ConfirmationDecision.megerosit)
    }
    
    response = state_machine.handle_message(chat_id, "Igen, helyes")
    
    # Ready confirmation triggers search and returns the formatted train list
    assert "Elérhető vonatok:" in response
    assert "1. IC 503" in response
    assert "Melyiket szeretnéd?" in response
    
    # DB state transitions
    session = session_store.get(chat_id)
    assert session["state"] == state_machine.STATE_WAITING_FOR_CONFIRMATION_2
    assert len(session["search_results"]) == 3


@patch("orchestrator.state_machine.parse_confirmation")
def test_handle_waiting_for_first_confirmation_modosit(mock_parse):
    chat_id = 123456
    session_store.set(chat_id, {
        "state": state_machine.STATE_WAITING_FOR_CONFIRMATION_1,
        "ticket_request": {"departure_station": "Budapest", "destination_station": "Szeged"},
        "message_history": []
    })
    
    mock_parse.return_value = {
        "status": "ready",
        "data": ConfirmationResponse(
            decision=ConfirmationDecision.modosit,
            fields_to_modify={"departure_station": "Debrecen"}
        )
    }
    
    response = state_machine.handle_message(chat_id, "nem, Debrecenből")
    
    assert "Indulás:        Debrecen" in response
    assert "Érkezés:        Szeged" in response
    
    # State remains
    session = session_store.get(chat_id)
    assert session["state"] == state_machine.STATE_WAITING_FOR_CONFIRMATION_1
    assert session["ticket_request"].departure_station == "Debrecen"


@patch("orchestrator.state_machine.parse_confirmation")
def test_handle_waiting_for_first_confirmation_elutasit(mock_parse):
    chat_id = 123456
    session_store.set(chat_id, {
        "state": state_machine.STATE_WAITING_FOR_CONFIRMATION_1,
        "ticket_request": {"departure_station": "Budapest"},
        "message_history": []
    })
    
    mock_parse.return_value = {
        "status": "ready",
        "data": ConfirmationResponse(decision=ConfirmationDecision.megszakit)
    }
    
    response = state_machine.handle_message(chat_id, "mégse kérem")
    
    assert "Rendben, a foglalás megszakítva" in response
    
    # Session is deleted, calling get returns default
    session = session_store.get(chat_id)
    assert session["state"] == state_machine.STATE_WAITING_FOR_REQUEST
    assert session["updated_at"] is None


@patch("orchestrator.state_machine.parse_offer_selection")
def test_handle_offer_selection_none_suitable(mock_parse):
    chat_id = 123456
    session_store.set(chat_id, {
        "state": state_machine.STATE_WAITING_FOR_CONFIRMATION_2,
        "search_results": [{"train": "IC 503", "price": 3890}],
        "message_history": []
    })
    
    mock_parse.return_value = {
        "status": "ready",
        "data": OfferSelection(none_suitable=True)
    }
    
    response = state_machine.handle_message(chat_id, "egyik se jó")
    
    assert "kezdjük elölről" in response
    session = session_store.get(chat_id)
    assert session["state"] == state_machine.STATE_WAITING_FOR_REQUEST


@patch("orchestrator.state_machine.parse_offer_selection")
def test_handle_offer_selection_valid(mock_parse):
    chat_id = 123456
    session_store.set(chat_id, {
        "state": state_machine.STATE_WAITING_FOR_CONFIRMATION_2,
        "search_results": [
            {"train": "IC 503", "departure": "14:05", "arrival": "16:55", "price": 3890},
            {"train": "IC 701", "departure": "16:05", "arrival": "18:55", "price": 4200}
        ],
        "message_history": []
    })
    
    mock_parse.return_value = {
        "status": "ready",
        "data": OfferSelection(selected_index=1)
    }
    
    response = state_machine.handle_message(chat_id, "a másodikat")
    
    assert "Vegso megerosites:" in response
    assert "Vonat:    IC 701" in response
    assert "Indulás:  16:05" in response
    assert "Érkezés:  18:55" in response
    assert "Ár:       4 200 Ft" in response
    assert "Biztosan fizetek? (igen / nem)" in response
    
    session = session_store.get(chat_id)
    assert session["state"] == state_machine.STATE_PAYING
    assert session["selected_offer"]["train"] == "IC 701"


@patch("orchestrator.state_machine.parse_offer_selection")
def test_handle_offer_selection_invalid(mock_parse):
    chat_id = 123456
    session_store.set(chat_id, {
        "state": state_machine.STATE_WAITING_FOR_CONFIRMATION_2,
        "search_results": [{"train": "IC 503", "price": 3890}],
        "message_history": []
    })
    
    mock_parse.return_value = {
        "status": "ready",
        "data": OfferSelection(selected_index=5)  # Out of bounds
    }
    
    response = state_machine.handle_message(chat_id, "ötödik")
    
    assert "Érvénytelen választás" in response
    session = session_store.get(chat_id)
    assert session["state"] == state_machine.STATE_WAITING_FOR_CONFIRMATION_2


@patch("orchestrator.state_machine.parse_confirmation")
def test_handle_payment_confirm(mock_parse):
    chat_id = 123456
    selected_offer = {"train": "IC 503", "price": 3890}
    session_store.set(chat_id, {
        "state": state_machine.STATE_PAYING,
        "selected_offer": selected_offer,
        "message_history": []
    })
    
    mock_parse.return_value = {
        "status": "ready",
        "data": ConfirmationResponse(decision=ConfirmationDecision.megerosit)
    }
    
    response = state_machine.handle_message(chat_id, "igen, fizessük")
    
    assert "jegy sikeresen megvasarolva" in response.lower()
    
    # Session should be deleted
    session = session_store.get(chat_id)
    assert session["state"] == state_machine.STATE_WAITING_FOR_REQUEST
    
    # Check transaction log file
    assert os.path.exists("logs/transactions.jsonl")
    with open("logs/transactions.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["status"] == "sikeres"
        assert entry["chat_id"] == chat_id
        assert entry["offer"] == selected_offer


@patch("orchestrator.state_machine.parse_confirmation")
def test_handle_payment_cancel(mock_parse):
    chat_id = 123456
    session_store.set(chat_id, {
        "state": state_machine.STATE_PAYING,
        "selected_offer": {"train": "IC 503", "price": 3890},
        "message_history": []
    })
    
    mock_parse.return_value = {
        "status": "ready",
        "data": ConfirmationResponse(decision=ConfirmationDecision.megszakit)
    }
    
    response = state_machine.handle_message(chat_id, "nem, mégse")
    
    assert "Fizetés megszakítva" in response
    
    session = session_store.get(chat_id)
    assert session["state"] == state_machine.STATE_WAITING_FOR_REQUEST
    
    # Check transaction log file
    assert os.path.exists("logs/transactions.jsonl")
    with open("logs/transactions.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["status"] == "megszakitva"
        assert entry["chat_id"] == chat_id
        assert entry["reason"] == "user_cancel"


def test_handle_message_unexpected_state():
    chat_id = 123456
    session_store.set(chat_id, {
        "state": "UNKNOWN_STATE_123",
        "message_history": []
    })
    
    response = state_machine.handle_message(chat_id, "hallo")
    assert "Váratlan hiba történt" in response
    
    session = session_store.get(chat_id)
    assert session["state"] == state_machine.STATE_WAITING_FOR_REQUEST


@patch("orchestrator.state_machine.parse_ticket_request")
def test_handle_message_exception_in_handler(mock_parse):
    chat_id = 123456
    mock_parse.side_effect = Exception("API connection crash")
    
    response = state_machine.handle_message(chat_id, "Szia")
    assert "Váratlan hiba történt" in response
    
    session = session_store.get(chat_id)
    assert session["state"] == state_machine.STATE_WAITING_FOR_REQUEST
