# MAV Ticket Agent - Development Tasks (TODO)

This document contains the development roadmap, pending tasks, and priorities for the MAV Ticket Agent.

---

## Phase 1: Playwright Booking Automation (booking/)

Implementing the core browser automation using browser_session.py and selectors.py.

- [ ] **MAV Login**: Automatic authentication using the provided email/password credentials if no valid auth_state.json exists.
- [ ] **Search Form Submission**: Inputting departure and destination stations, along with the date/time on jegy.mav.hu.
- [ ] **Scraping Search Results**: Retrieving the list of available trains (train number, departure/arrival time, travel duration, price) from the search results and returning them in a structured format.
- [ ] **Passenger Details and Discounts**: Setting the number of passengers and passenger types (e.g., student, adult) on the interface based on the TicketRequest.
- [ ] **Seat Reservation Preferences**: Selecting seat preferences (window, aisle, table, or compartment seat) based on selectors.

---

## Phase 2: Orchestration and Integration

Wiring the background processes together and replacing mocked data.

- [ ] **Replace Mock Search**: Rewriting the _handle_searching method in state_machine.py to invoke the real Playwright search script.
- [ ] **Asynchronous Execution**: Running browser automation as a background async task so it does not block the Telegram bot's other handlers during waits.
- [ ] **Dry-Run Payment Protection**: Ensuring that when DRY_RUN=true, the automation stops before the final payment button and saves a screenshot for verification.

---

## Phase 3: Telegram Bot User Experience (telegram_bot/)

Improving user interactions and delivering purchased tickets.

- [ ] **Inline Keyboards (Buttons)**:
  - Approving or modifying the initial ticket summary using buttons instead of plain text responses.
  - Displaying numbered buttons during train selection to allow easy selection.
- [ ] **PDF Ticket Delivery**: Sending the downloaded MAV ticket as a PDF document to the user on Telegram upon successful purchase.
- [ ] **Status Updates**: Sending progress status messages to the user (e.g., "Searching...", "Logging into MAV account...").

---

## Phase 4: Testing and Fault Tolerance

Ensuring code quality and stability.

- [ ] **NLU Unit Tests**: Writing unit tests for parser.py with various user inputs (e.g., missing station names, different date formats).
- [ ] **Session Expiration Tests**: Verifying that the session_store deletes inactive sessions from the SQLite database after 15 minutes of inactivity.
- [ ] **Automation Error Handling**: Implementing proper error notification and session reset in case the MAV website crashes, slows down, or changes its selectors.
