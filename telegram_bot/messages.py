"""
This module centralizes all user-facing message constants and string formatting functions
for the booking system orchestrator. No conversational logic is contained here.
"""

# Static Constants
MSG_SEARCHING = "Keresem az elérhető vonatokat..."

MSG_CANCEL = (
    "Rendben, a foglalás megszakítva.\n"
    "Ha újat szeretnél indítani, csak írj!"
)

MSG_PAYMENT_SUCCESS = (
    "A jegy sikeresen megvasarolva.\n"
    "Jo utat!"
)

MSG_PAYMENT_CANCELLED = (
    "Fizetés megszakítva.\n"
    "Ha újra szeretnél foglalni, csak írj!"
)

MSG_UNAUTHORIZED = (
    "Nincs jogosultságod ezt a botot használni."
)

MSG_ERROR = (
    "Váratlan hiba történt, a foglalás megszakadt.\n"
    "Kérlek kezdd újra."
)

MSG_INVALID_SELECTION = (
    "Érvénytelen választás, kérlek válassz a listából!"
)

MSG_RESTART = (
    "Rendben, kezdjük elölről!\n"
    "Írj egy új jegykérést."
)


# Formatting Functions
def format_ticket_summary(ticket_request: dict) -> str:
    """
    Formats the parsed TicketRequest dict to a human-readable Hungarian summary
    for the first confirmation step.
    """
    departure_station = ticket_request.get("departure_station") or ""
    destination_station = ticket_request.get("destination_station") or ""
    departure_time_raw = ticket_request.get("departure_time_raw") or ticket_request.get("departure_time_iso") or ""

    # Format passengers: "{count}x {passenger_type}"
    passengers_raw = ticket_request.get("passengers") or []
    passengers_list = []
    for p in passengers_raw:
        if isinstance(p, dict):
            p_type = p.get("passenger_type")
            count = p.get("count", 1)
        else:
            p_type = getattr(p, "passenger_type", None)
            count = getattr(p, "count", 1)

        if p_type is not None:
            p_type_val = getattr(p_type, "value", p_type)
            passengers_list.append(f"{count}x {p_type_val}")

    passengers_str = ", ".join(passengers_list)

    # Format ticket class
    tc = ticket_request.get("ticket_class")
    if tc is None:
        ticket_class_str = "2. osztály (alapértelmezett)"
    else:
        tc_val = getattr(tc, "value", tc)
        if tc_val == "1":
            ticket_class_str = "1. osztály"
        elif tc_val == "2":
            ticket_class_str = "2. osztály"
        else:
            ticket_class_str = f"{tc_val}. osztály" if tc_val else "2. osztály (alapértelmezett)"

    # Format seat preferences
    seat_prefs = ticket_request.get("seat_preferences") or []
    seat_pref_vals = [str(getattr(sp, "value", sp)) for sp in seat_prefs]
    if seat_pref_vals:
        seat_pref_str = ", ".join(seat_pref_vals)
    else:
        seat_pref_str = "nincs megadva"

    # Format extras
    extras = ticket_request.get("extras") or []
    extra_vals = [str(getattr(ex, "value", ex)) for ex in extras]
    if extra_vals:
        extras_str = ", ".join(extra_vals)
    else:
        extras_str = "nincs"

    return (
        "Ezt értettem:\n\n"
        f"Indulás:        {departure_station}\n"
        f"Érkezés:        {destination_station}\n"
        f"Időpont:        {departure_time_raw}\n"
        f"Utasok:         {passengers_str}\n"
        f"Osztály:        {ticket_class_str}\n"
        f"Helytulajdonság: {seat_pref_str}\n"
        f"Extra:          {extras_str}\n\n"
        "Helyes? (igen / nem / mondd meg mit változtassak)"
    )


def format_search_results(results: list) -> str:
    """
    Formats the mock/real search results for the second confirmation step.
    """
    lines = ["Elérhető vonatok:\n"]
    for i, item in enumerate(results, start=1):
        train = item.get("train", "")
        departure = item.get("departure", "")
        arrival = item.get("arrival", "")
        duration = item.get("duration", "")
        price = item.get("price", 0)
        price_formatted = f"{price:,}".replace(",", " ")
        lines.append(f"{i}. {train} — {departure} > {arrival} ({duration}) — {price_formatted} Ft")

    lines.append("\nMelyiket szeretnéd?\n(Válaszolj a sorszámmal vagy írj le, melyiket választod)")
    return "\n".join(lines)


def format_final_confirmation(offer: dict) -> str:
    """
    Formats the final confirmation summary before payment.
    """
    train = offer.get("train", "")
    departure = offer.get("departure", "")
    arrival = offer.get("arrival", "")
    duration = offer.get("duration", "")
    price = offer.get("price", 0)
    price_formatted = f"{price:,}".replace(",", " ")

    return (
        "Vegso megerosites:\n\n"
        f"Vonat:    {train}\n"
        f"Indulás:  {departure}\n"
        f"Érkezés:  {arrival}\n"
        f"Menetidő: {duration}\n"
        f"Ár:       {price_formatted} Ft\n\n"
        "Biztosan fizetek? (igen / nem)"
    )
