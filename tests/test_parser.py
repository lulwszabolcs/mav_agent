import pytest
from unittest.mock import patch
from nlu.parser import parse_ticket_request, parse_confirmation, parse_offer_selection
from nlu.schema import TicketRequest, ConfirmationResponse, OfferSelection, ConfirmationDecision

def test_parse_ticket_request_success():
    mock_payload = {
        "departure_station": "Budapest",
        "destination_station": "Szeged",
        "departure_time_iso": "2026-06-23T14:30",
        "passengers": [{"passenger_type": "felnott", "count": 1}]
    }
    with patch("nlu.parser.client.call") as mock_call:
        mock_call.return_value = ("TicketRequest", mock_payload)
        
        result = parse_ticket_request([])
        assert result["status"] == "ready"
        assert isinstance(result["data"], TicketRequest)
        assert result["data"].departure_station == "Budapest"
        assert result["data"].destination_station == "Szeged"
        assert len(result["data"].passengers) == 1

def test_parse_ticket_request_validation_error():
    mock_payload = {
        "departure_station": "Budapest",
        "passengers": [{"passenger_type": "INVALID_TYPE", "count": 1}]
    }
    with patch("nlu.parser.client.call") as mock_call:
        mock_call.return_value = ("TicketRequest", mock_payload)
        
        result = parse_ticket_request([])
        assert result["status"] == "needs_clarification"
        assert "message" in result

def test_parse_ticket_request_text_response():
    with patch("nlu.parser.client.call") as mock_call:
        mock_call.return_value = (None, "Melyik állomásról szeretne indulni?")
        
        result = parse_ticket_request([])
        assert result["status"] == "needs_clarification"
        assert result["message"] == "Melyik állomásról szeretne indulni?"

def test_parse_ticket_request_none_none():
    with patch("nlu.parser.client.call") as mock_call:
        mock_call.return_value = (None, None)
        
        result = parse_ticket_request([])
        assert result["status"] == "needs_clarification"
        assert result["message"] == "Nem sikerült értelmezni a kérést."

def test_parse_confirmation_success():
    mock_payload = {
        "decision": "modosit",
        "fields_to_modify": {"departure_station": "Debrecen"}
    }
    with patch("nlu.parser.client.call") as mock_call:
        mock_call.return_value = ("ConfirmationResponse", mock_payload)
        
        result = parse_confirmation([])
        assert result["status"] == "ready"
        assert isinstance(result["data"], ConfirmationResponse)
        assert result["data"].decision == ConfirmationDecision.modosit
        assert result["data"].fields_to_modify == {"departure_station": "Debrecen"}

def test_parse_confirmation_validation_error():
    mock_payload = {
        "decision": "UNKNOWN_DECISION"
    }
    with patch("nlu.parser.client.call") as mock_call:
        mock_call.return_value = ("ConfirmationResponse", mock_payload)
        
        result = parse_confirmation([])
        assert result["status"] == "needs_clarification"
        assert "message" in result

def test_parse_offer_selection_success():
    mock_payload = {
        "selected_index": 2,
        "none_suitable": False
    }
    with patch("nlu.parser.client.call") as mock_call:
        mock_call.return_value = ("OfferSelection", mock_payload)
        
        result = parse_offer_selection([])
        assert result["status"] == "ready"
        assert isinstance(result["data"], OfferSelection)
        assert result["data"].selected_index == 2
        assert not result["data"].none_suitable

def test_parse_offer_selection_none_none():
    with patch("nlu.parser.client.call") as mock_call:
        mock_call.return_value = (None, None)
        
        result = parse_offer_selection([])
        assert result["status"] == "needs_clarification"
        assert result["message"] == "Nem sikerült értelmezni a választást."
