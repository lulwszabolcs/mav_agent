import os
import json
import logging
import pytest
import sqlite3
from unittest.mock import patch
import orchestrator.session_store as session_store
from nlu.schema import TicketRequest, Passenger, PassengerType


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """
    Fixture to automatically redirect the database path to a temporary file
    and reset ALLOWED_CHAT_IDS configuration for isolation.
    """
    # Override database path to temporary file
    original_db_path = session_store.DB_PATH
    temp_db = tmp_path / "test_sessions.db"
    session_store.DB_PATH = str(temp_db)
    
    # Configure default allowed chat IDs for testing
    original_allowed_ids = session_store.ALLOWED_CHAT_IDS
    session_store.ALLOWED_CHAT_IDS = [123456, 987654]
    
    yield temp_db
    
    # Restore original configurations
    session_store.DB_PATH = original_db_path
    session_store.ALLOWED_CHAT_IDS = original_allowed_ids


def test_validate_chat_id():
    # Allowed chat ID (int or str representation) should pass
    assert session_store._validate_chat_id(123456) == 123456
    assert session_store._validate_chat_id("987654") == 987654
    
    # Non-allowed or invalid formats should raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        session_store._validate_chat_id(999999)
    assert "Access denied for chat_id" in str(exc_info.value)
    
    with pytest.raises(PermissionError) as exc_info:
        session_store._validate_chat_id("abc")
    assert "Invalid chat_id format" in str(exc_info.value)


def test_permission_checks_on_public_methods():
    # Verify that get, set, delete raise PermissionError if chat_id is not allowed
    invalid_chat_id = 999999
    
    with pytest.raises(PermissionError):
        session_store.get(invalid_chat_id)
        
    with pytest.raises(PermissionError):
        session_store.set(invalid_chat_id, {"state": "vár_kérésre"})
        
    with pytest.raises(PermissionError):
        session_store.delete(invalid_chat_id)


def test_get_default_session(setup_test_db):
    chat_id = 123456
    session = session_store.get(chat_id)
    
    assert session["chat_id"] == chat_id
    assert session["state"] == "vár_kérésre"
    assert session["ticket_request"] is None
    assert session["search_results"] is None
    assert session["message_history"] == []
    assert session["updated_at"] is None


def test_set_and_get_basic_session(setup_test_db):
    chat_id = 123456
    session_data = {
        "state": "keres",
        "ticket_request": None,
        "search_results": {"trains": [{"id": 1, "price": 4500}]},
        "message_history": [{"role": "user", "content": "Jegy Szegedre"}]
    }
    
    session_store.set(chat_id, session_data)
    
    retrieved = session_store.get(chat_id)
    assert retrieved["chat_id"] == chat_id
    assert retrieved["state"] == "keres"
    assert retrieved["ticket_request"] is None
    assert retrieved["search_results"] == {"trains": [{"id": 1, "price": 4500}]}
    assert retrieved["message_history"] == [{"role": "user", "content": "Jegy Szegedre"}]
    assert retrieved["updated_at"] is not None


def test_set_with_pydantic_model(setup_test_db):
    chat_id = 123456
    
    pydantic_request = TicketRequest(
        departure_station="Budapest",
        destination_station="Szeged",
        passengers=[Passenger(passenger_type=PassengerType.felnott, count=2)]
    )
    
    session_data = {
        "state": "vár_megerősítés_1",
        "ticket_request": pydantic_request,
        "search_results": None,
        "message_history": []
    }
    
    session_store.set(chat_id, session_data)
    
    # Retrieve and verify it is deserialized back to TicketRequest Pydantic object
    retrieved = session_store.get(chat_id)
    assert retrieved["state"] == "vár_megerősítés_1"
    
    retrieved_request = retrieved["ticket_request"]
    assert isinstance(retrieved_request, TicketRequest)
    assert retrieved_request.departure_station == "Budapest"
    assert retrieved_request.destination_station == "Szeged"
    assert len(retrieved_request.passengers) == 1
    assert retrieved_request.passengers[0].passenger_type == PassengerType.felnott
    assert retrieved_request.passengers[0].count == 2


def test_delete_session(setup_test_db):
    chat_id = 123456
    session_data = {
        "state": "fizet",
        "ticket_request": None,
        "search_results": None,
        "message_history": []
    }
    
    # Save
    session_store.set(chat_id, session_data)
    # Ensure it is saved
    assert session_store.get(chat_id)["state"] == "fizet"
    
    # Delete
    session_store.delete(chat_id)
    
    # Verify it is deleted (returns default session)
    deleted_session = session_store.get(chat_id)
    assert deleted_session["state"] == "vár_kérésre"
    assert deleted_session["updated_at"] is None


def test_delete_non_existent_chat_id_is_silent(setup_test_db):
    chat_id = 123456
    # Deleting non-existent allowed chat ID should not raise any error (silent)
    try:
        session_store.delete(chat_id)
    except Exception as e:
        pytest.fail(f"delete() raised an exception on non-existent chat: {e}")


def test_logging_calls(caplog):
    # Set logging level to INFO for capturing
    caplog.set_level(logging.INFO)
    chat_id = 123456
    
    session_store.get(chat_id)
    assert f"session_store | get | chat_id={chat_id}" in caplog.text
    
    session_store.set(chat_id, {"state": "vár_kérésre"})
    assert f"session_store | set | chat_id={chat_id}" in caplog.text
    
    session_store.delete(chat_id)
    assert f"session_store | delete | chat_id={chat_id}" in caplog.text


def test_db_auto_creation_and_directory(tmp_path):
    # Tests that data/ and sessions.db are created automatically if they do not exist
    test_dir = tmp_path / "nested" / "data"
    test_db = test_dir / "test_sessions.db"
    
    # Set non-existent path
    session_store.DB_PATH = str(test_db)
    
    # Check directory does not exist yet
    assert not test_dir.exists()
    
    # Initializing DB / reading should trigger folder and file creation
    session_store.get(123456)
    
    assert test_dir.exists()
    assert test_db.exists()
