"""
This module implements the state-dependent message parser.
It processes conversation history, makes structured API calls using XAIClient,
and validates the returned schemas using Pydantic models.
"""

from typing import List, Dict, Any
from pydantic import ValidationError

from nlu.client import XAIClient
from nlu.schema import (
    TicketRequest,
    ConfirmationResponse,
    OfferSelection,
    to_xai_tool,
)

# Instantiate the global client
client = XAIClient()

def parse_ticket_request(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Parses a train ticket request from conversation history using TicketRequest schema.
    If mandatory fields (departure_station, destination_station, departure_time_iso)
    are missing or ambiguous, the model is instructed to ask for clarification instead of calling the tool.
    """
    tool_def = to_xai_tool(TicketRequest)
    
    system_prompt = (
        "Te egy segítőkész MÁV vonatjegy-foglaló asszisztens vagy. "
        "A feladatod a felhasználó jegyigényeinek strukturált kinyerése a TicketRequest eszközzel.\n\n"
        "FONTOS SZABÁLY:\n"
        "Ha az indulási állomás (departure_station), az érkezési állomás (destination_station) "
        "vagy a gép által értelmezhető indulási idő (departure_time_iso) hiányzik a beszélgetésből "
        "vagy kétértelmű, SOHA NE hívd meg a TicketRequest eszközt. Ehelyett válaszolj magyarul, "
        "és kérdezz rá a hiányzó vagy nem egyértelmű információkra."
    )
    
    tool_name, payload = client.call([tool_def], system_prompt, messages)
    
    if tool_name is not None and payload is not None:
        try:
            data = TicketRequest.model_validate(payload)
            return {"status": "ready", "data": data}
        except ValidationError as e:
            return {"status": "needs_clarification", "message": str(e)}
            
    if isinstance(payload, str):
        return {"status": "needs_clarification", "message": payload}
        
    return {"status": "needs_clarification", "message": "Nem sikerült értelmezni a kérést."}

def parse_confirmation(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Parses the user's response to a confirmation request using ConfirmationResponse schema.
    Classifies the user's decision (megerosit, elutasit, modosit, megszakit).
    If modification is requested, details are placed in fields_to_modify.
    """
    tool_def = to_xai_tool(ConfirmationResponse)
    
    system_prompt = (
        "Te egy MÁV vonatjegy-foglaló asszisztens vagy. "
        "A feladatod a felhasználó megerősítési kérdésre adott válaszának osztályozása a ConfirmationResponse eszközzel.\n\n"
        "Határozd meg a felhasználó döntését (decision):\n"
        "- 'megerosit': ha a felhasználó egyértelműen megerősíti és elfogadja az adatokat/ajánlatot.\n"
        "- 'elutasit': ha elutasítja a megerősítést, de nem szakítja meg teljesen a folyamatot.\n"
        "- 'modosit': ha módosítani szeretné valamelyik adatot. Ekkor a 'fields_to_modify' szótárba tedd be a módosítani kívánt mezőket és az új értéküket.\n"
        "- 'megszakit': ha meg akarja szakítani a teljes foglalási folyamatot.\n\n"
        "Kérlek, mindenképp hívd meg a ConfirmationResponse eszközt a megfelelő paraméterekkel."
    )
    
    tool_name, payload = client.call([tool_def], system_prompt, messages)
    
    if tool_name is not None and payload is not None:
        try:
            data = ConfirmationResponse.model_validate(payload)
            return {"status": "ready", "data": data}
        except ValidationError as e:
            return {"status": "needs_clarification", "message": str(e)}
            
    if isinstance(payload, str):
        return {"status": "needs_clarification", "message": payload}
        
    return {"status": "needs_clarification", "message": "Nem sikerült értelmezni a megerősítésre adott választ."}

def parse_offer_selection(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Parses the user's selection from presented train offers using OfferSelection schema.
    Identifies the 0-indexed selected offer, or flags none_suitable if the user rejects them.
    """
    tool_def = to_xai_tool(OfferSelection)
    
    system_prompt = (
        "Te egy MÁV vonatjegy-foglaló asszisztens vagy. "
        "A feladatod a felkínált vonatajánlatok közüli felhasználói választás értelmezése az OfferSelection eszközzel.\n\n"
        "- Ha a felhasználó kiválasztotta az egyik felkínált ajánlatot, add meg a kiválasztott ajánlat 0-alapú indexét a 'selected_index' mezőben.\n"
        "- Ha egyik ajánlat sem megfelelő a felhasználónak és újat szeretne keresni, állítsd a 'none_suitable' értéket True-ra.\n\n"
        "Kérlek, mindenképp hívd meg az OfferSelection eszközt a megfelelő paraméterekkel."
    )
    
    tool_name, payload = client.call([tool_def], system_prompt, messages)
    
    if tool_name is not None and payload is not None:
        try:
            data = OfferSelection.model_validate(payload)
            return {"status": "ready", "data": data}
        except ValidationError as e:
            return {"status": "needs_clarification", "message": str(e)}
            
    if isinstance(payload, str):
        return {"status": "needs_clarification", "message": payload}
        
    return {"status": "needs_clarification", "message": "Nem sikerült értelmezni a választást."}
