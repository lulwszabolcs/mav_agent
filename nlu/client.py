"""
This module implements a thin wrapper client around the xAI (Grok) API.
It is responsible for low-level communication with the API, handling conversation history formatting,
and returning structured function calling tool outputs or text responses.
"""

import os
import json
from typing import List, Optional, Tuple, Type, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Verify API key availability at module load time
XAI_API_KEY = os.environ.get("XAI_API_KEY")
if not XAI_API_KEY:
    raise ValueError(
        "XAI_API_KEY environment variable is missing. "
        "Please configure it in your environment or .env file."
    )

from xai_sdk import Client
from xai_sdk.chat import system, user, assistant

# Default system prompt for the MÁV AI booking assistant
DEFAULT_SYSTEM_PROMPT = (
    "Te egy segítőkész MÁV vonatjegy-foglaló asszisztens vagy, aki egy Telegram csatornán keresztül kommunikál a felhasználókkal.\n"
    "Kérlek, kövesd az alábbi szabályokat:\n"
    "1. Mindig válaszolj magyarul.\n"
    "2. Ha a felhasználó szándéka vagy a megadott adatok bármelyike nem teljesen egyértelmű, kérdezz vissza udvariasan a hiányzó vagy kétértelmű részletekre, ne találj ki és ne tippelj meg adatokat.\n"
    "3. SOHA ne hívj meg foglalási eszközt (tool-t), ha az indulási állomás (departure_station), az érkezési állomás (destination_station) vagy az indulási idő ISO formátuma (departure_time_iso) hiányzik vagy kétértelmű."
)

class XAIClientError(Exception):
    """Raised when there is an issue communicating with the xAI API."""
    pass

class XAIClient:
    """
    Thin wrapper client around the xAI (Grok) API for ticket booking NLU processing.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "grok-4.3"):
        self.api_key = api_key or XAI_API_KEY
        if not self.api_key:
            raise ValueError("XAI_API_KEY must be provided.")
        self.client = Client(api_key=self.api_key)
        self.model = model

    def call(
        self, 
        tools: List[Any], 
        system_prompt: str, 
        messages: List[Dict[str, str]]
    ) -> Tuple[Optional[str], Optional[Any]]:
        """
        Sends the chat history and system prompt to xAI API and returns the result.

        Args:
            tools: List of xAI tool definitions (from schema.py).
            system_prompt: The system prompt guiding the assistant's behavior.
            messages: Full conversation history list, e.g. [{"role": "user", "content": "..."}].

        Returns:
            A tuple of (tool_name, payload_dict) if a tool call was triggered,
            (None, text_response) if the model responded with text,
            or (None, None) if neither occurred.
        """
        # Build chat messages sequence
        formatted_messages = []
        if system_prompt:
            formatted_messages.append(system(system_prompt))

        # Convert conversation history
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "system":
                formatted_messages.append(system(content))
            elif role == "user":
                formatted_messages.append(user(content))
            elif role == "assistant":
                formatted_messages.append(assistant(content))

        try:
            # Create a chat session
            chat = self.client.chat.create(
                model=self.model,
                messages=formatted_messages,
                tools=tools if tools else None
            )
            # Sample the response from the model
            response = chat.sample()
        except Exception as e:
            raise XAIClientError(f"Failed to communicate with xAI API: {e}") from e

        # Handle tool calls
        if response.tool_calls:
            tc = response.tool_calls[0]
            try:
                payload = json.loads(tc.function.arguments)
            except Exception as e:
                raise XAIClientError(f"Failed to parse tool call arguments as JSON: {e}") from e
            return tc.function.name, payload

        # Handle text response
        if response.content:
            return None, response.content

        return None, None
