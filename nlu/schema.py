"""
This module defines the Pydantic schemas and helper functions used for Natural Language Understanding (NLU).
It includes structured ticket request definitions and utility functions to convert Pydantic models to xAI tools.
"""

from enum import Enum
from typing import List, Optional, Type
from pydantic import BaseModel, Field
from xai_sdk.chat import tool

class TicketClass(str, Enum):
    elso = "1"
    masodik = "2"

class PassengerType(str, Enum):
    felnott = "felnott"
    diak_26_alatt = "diak_26_alatt"
    diak_26_felett = "diak_26_felett"
    nyugdijas = "nyugdijas"
    hatvanot_felett = "hatvanot_felett"
    gyerek = "gyerek"

class SeatPreference(str, Enum):
    ablak = "ablak"
    folyoso = "folyoso"
    asztal = "asztal"
    fulkes = "fulkes"
    termes = "termes"

class Passenger(BaseModel):
    """
    Represents a passenger with their discount type and count.
    """
    passenger_type: PassengerType = Field(
        ...,
        description="A passenger or discount type."
    )
    count: int = Field(
        default=1,
        description="Number of passengers belonging to this type."
    )

class TicketRequest(BaseModel):
    """
    Represents a structured train ticket request parsed from a Hungarian prompt.
    """
    departure_station: Optional[str] = Field(
        default=None,
        description="The departure station (honnan). E.g., 'Budapest', 'Győr', 'Debrecen'."
    )
    destination_station: Optional[str] = Field(
        default=None,
        description="The destination station (hova). E.g., 'Szeged', 'Pécs', 'Sopron'."
    )
    departure_time_raw: Optional[str] = Field(
        default=None,
        description="The departure date/time as written by the user. E.g., 'ma délután', 'holnap reggel'."
    )
    departure_time_iso: Optional[str] = Field(
        default=None,
        description="The departure date/time resolved/parsed into ISO 8601 format (YYYY-MM-DDTHH:MM). E.g., '2026-06-23T14:30'."
    )
    passengers: List[Passenger] = Field(
        default_factory=list,
        description="List of passengers and their specific discounts/types."
    )
    ticket_class: Optional[TicketClass] = Field(
        default=None,
        description="The requested carriage/travel class (1 for 1st class, 2 for 2nd class)."
    )
    seat_preferences: List[SeatPreference] = Field(
        default_factory=list,
        description="List of seat preferences."
    )
    extras: List[str] = Field(
        default_factory=list,
        description="List of extra requests (e.g. 'kerekpar', 'kutya')."
    )

def to_xai_tool(model: Type[BaseModel], name: Optional[str] = None, description: Optional[str] = None):
    """
    Builds an xAI function calling tool definition from a Pydantic model.
    Enforces strict schemas recursively and removes redundant metadata to optimize tokens.
    """
    schema = model.model_json_schema()
    
    # Helper to recursively clean up metadata and enforce strict schema
    def clean_schema(item):
        if isinstance(item, dict):
            # Remove title metadata to save tokens
            item.pop("title", None)
            
            # Enforce strict schema on all objects (required for structured outputs)
            if item.get("type") == "object":
                item["additionalProperties"] = False
                
            for key, val in list(item.items()):
                clean_schema(val)
        elif isinstance(item, list):
            for entry in item:
                clean_schema(entry)

    clean_schema(schema)
    
    # Explicitly enforce additionalProperties: False on nested defs (e.g., Passenger)
    for defn in schema.get("$defs", {}).values():
        defn["additionalProperties"] = False
        
    tool_name = name or model.__name__
    tool_description = description or model.__doc__ or f"Run {tool_name} tool."
    tool_description = tool_description.strip()
    
    return tool(name=tool_name, description=tool_description, parameters=schema)
