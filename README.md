# MÁV Ticket Agent 🚆

An AI agent that buys Hungarian train tickets for you through Telegram. Tell it where you want to go — it handles the rest.
 
## How it works
 
The user sends a message in natural Hungarian to the Telegram bot, describing the ticket. The agent understands the request, searches for available trains on [jegy.mav.hu](https://jegy.mav.hu), and walks the user through the booking — asking for confirmation at every critical step before any real transaction is made.

## Architecture
 
The agent is split into three independent layers:
 
**NLU layer** — Powered by the Grok API (xAI). Parses your natural language message into a structured ticket request using function calling and Pydantic schemas. Handles ambiguous input by asking follow-up questions before proceeding.
 
**Orchestration layer** — A per-user state machine that tracks where each conversation is in the booking flow. Persists state in SQLite so nothing is lost between messages.
 
**Booking layer** — A Playwright-based browser automation module that operates jegy.mav.hu on your behalf: searching trains, selecting seats, and completing checkout. Payment credentials are handled in an isolated module and never passed to the AI or written to logs.