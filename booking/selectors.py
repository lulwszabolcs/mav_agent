"""
All jegy.mav.hu CSS/XPath selectors in one place.
If the page UI changes, only this file needs to be updated.
"""

# Main selector dictionary, grouped by logical steps.
SELECTORS = {
    # === 1. LOGIN ===
    "login_profile_popup_btn": "#profile-popup-button",  # Click to open the profile popup panel
    "login_register_btn": "#login",  # Login/Registration button on the opened panel
    "login_email_input": "#emailFie",  # Email input field
    "login_password_input": "#passwordFie",  # Password input field
    "login_submit_btn": "#login-btn",  # Login button to submit the form

    # === 2. SEARCH FORM ===
    "search_start_station": "#startStation-input",  # Departure station input field (textarea)
    "search_end_station": "#endStation-input",  # Destination station input field (textarea)
    "search_datepicker_toggle": "button.datepicker-toggler-button",  # Datepicker calendar toggler button
    "search_calendar_status": "h2[role='status']",  # Calendar status header for reading current month/year
    "search_next_month_btn": "button.nextMonth",  # Button to step to the next month in the calendar
    "search_date_btn": "li.dateButton",  # Date selection button in the calendar (to be filtered by text)
    "search_datepicker_save": "button.save-button",  # Optional calendar save (Rendben) button
    "search_time_input": "#travelStartTime-input",  # Departure time input field
    
    # WARNING: Position-based, fragile DOM-chain selector.
    "search_submit_btn": "#head-search-quick-search > app-head-search-normal > section > div > div > app-head-search-bottom > div.search-button-row > button",  # Search button to trigger the search

    # === 3. SEARCH RESULTS ===
    "route_item": "li.route-item",  # Route list item in the search results
    "route_stations": ".stations span",  # Station spans within the route item (first non-sr-only is departure, last is arrival)
    "route_departure_time": "app-time-with-delay-v2[timetype='departure'] span[role='listitem']",  # Departure time span
    "route_arrival_time": "app-time-with-delay-v2[timetype='arrival'] span[role='listitem']",  # Arrival time span
    "route_travel_time": ".travel-time",  # Travel time container (read without sr-only content)
    "route_transfers": ".transfers",  # Number of transfers container (read without sr-only content)
    
    # Note: To be formatted with f-string, e.g. f"button#showDetailButton{index}"
    "route_detail_toggle": "button#showDetailButton{index}",  # Detail toggle button. Replacement: {index}
    
    # Note: To be formatted with f-string, e.g. f"#detail{index}"
    "route_detail_panel": "#detail{index}",  # Detail panel container. Replacement: {index}
    
    "route_offer_button": "app-select-offer-button-with-tooltip button.ticket-button",  # Offer price / class ticket button

    # === 4. PASSENGER DETAILS ===
    "passengers_step_indicator": "app-step-passengers",  # Passenger step container/indicator element
    "passengers_next_btn": "app-step-passengers div.bottom-buttons button",  # Passenger step Next button

    # === 5. SEAT RESERVATION ===
    "seat_reservation_property_radio": "#property",  # Seat property preference radio button
    "seat_reservation_graphical_radio": "#graphical",  # Graphical seat reservation radio button
    "seat_reservation_property_next_btn": "app-step-seat-reservation-parameters div.bottom-action-row button",  # Seat property step Next button
    
    # Note: To be formatted with f-string, e.g. f"#car-{number}"
    "seat_graphical_car_block": "#car-{number}",  # Car block container on the graphical seat map. Replacement: {number}
    
    "seat_graphical_car_number": "span[style*='grid-area: 2 / 1']",  # Car number span within the car container
    "seat_graphical_car_image": "img",  # Car image element for class validation (src containing "1oszt.svg" or "2oszt.svg")
    "seat_graphical_seat_path": "path",  # Seat path element in the SVG structure
    
    # Note: To be formatted with f-string, e.g. f"#bg_{number}"
    "seat_graphical_seat_id": "#bg_{number}",  # Seat ID/number on the graphical seat map. Replacement: {number}
    
    "seat_graphical_next_btn": "#next-btn",  # Graphical seat reservation Next button (check active/inactive class)

    # === 6. SUMMARY & PAYMENT ===
    "cart_departure_station": "app-cart-summary .stations span:first-child",  # Cart summary departure station span
    "cart_arrival_station": "app-cart-summary .stations span:last-child",  # Cart summary arrival station span
    "cart_travel_date": "app-cart-summary .travel-date",  # Cart summary travel date
    "cart_total_price": "app-cart-summary section.sum .price",  # Cart summary total price
    "cart_accept_conditions": "#accept-checkbox",  # Accept conditions checkbox
    
    # WARNING: Position-based, fragile DOM-chain selector.
    "cart_pay_btn": "#sidenav-container > mat-sidenav-content > app-router-outlet-adapter > span > app-cart > main > div.wrapper > div > div.search-button-row.d-flex.justify-content-end.position-relative > button",  # Pay button to initiate transaction
}

# Selectors for seat preferences grouped by TicketRequest SeatPreference enum values.
SEAT_PREFERENCE_SELECTORS = {
    "ablak": "label[for='positionOfSeatSeatWindow0']",  # Window seat checkbox label (CSS selector)
    "folyoso": "label[for='positionOfSeatSeatGangway2']",  # Aisle seat checkbox label (CSS selector)
    "fulkes": "//input[@id='compartmentRequest#typeOfCoach2']",  # Compartment coach checkbox (XPath due to # character)
    "termes": "//input[@id='compartmentRequest#typeOfCoach3']",  # Open saloon coach checkbox (XPath due to # character)
    "asztal": "//input[@id='compartmentRequest#typeOfCoach5']",  # Table seat checkbox (XPath due to # character)
}
