import pytest
from telegram_bot.messages import (
    MSG_SEARCHING,
    MSG_CANCEL,
    MSG_PAYMENT_SUCCESS,
    MSG_PAYMENT_CANCELLED,
    MSG_UNAUTHORIZED,
    MSG_ERROR,
    MSG_INVALID_SELECTION,
    MSG_RESTART,
    format_ticket_summary,
    format_search_results,
    format_final_confirmation,
)

def test_constants():
    assert MSG_SEARCHING == "Keresem az elérhető vonatokat..."
    assert "megszakítva" in MSG_CANCEL
    assert "megvasarolva" in MSG_PAYMENT_SUCCESS
    assert "Fizetés megszakítva" in MSG_PAYMENT_CANCELLED
    assert MSG_UNAUTHORIZED == "Nincs jogosultságod ezt a botot használni."
    assert "Váratlan hiba történt" in MSG_ERROR
    assert MSG_INVALID_SELECTION == "Érvénytelen választás, kérlek válassz a listából!"
    assert "kezdjük elölről" in MSG_RESTART

def test_format_ticket_summary_full():
    req = {
        "departure_station": "Budapest",
        "destination_station": "Szeged",
        "departure_time_raw": "ma délután",
        "passengers": [
            {"passenger_type": "felnott", "count": 2},
            {"passenger_type": "diak_26_alatt", "count": 1}
        ],
        "ticket_class": "1",
        "seat_preferences": ["ablak", "asztal"],
        "extras": ["kerekpar"]
    }
    res = format_ticket_summary(req)
    
    assert "Indulás:        Budapest" in res
    assert "Érkezés:        Szeged" in res
    assert "Időpont:        ma délután" in res
    assert "Utasok:         2x felnott, 1x diak_26_alatt" in res
    assert "Osztály:        1. osztály" in res
    assert "Helytulajdonság: ablak, asztal" in res
    assert "Extra:          kerekpar" in res
    assert "Helyes? (igen / nem / mondd meg mit változtassak)" in res

def test_format_ticket_summary_defaults():
    req = {
        "departure_station": "Budapest",
        "destination_station": "Szeged",
        "departure_time_raw": "ma délután",
        "passengers": [],
        "ticket_class": None,
        "seat_preferences": [],
        "extras": []
    }
    res = format_ticket_summary(req)
    
    assert "Utasok:         " in res
    assert "Osztály:        2. osztály (alapértelmezett)" in res
    assert "Helytulajdonság: nincs megadva" in res
    assert "Extra:          nincs" in res

def test_format_search_results():
    results = [
        {"train": "IC 503", "departure": "14:05", "arrival": "16:55", "duration": "2h 50m", "price": 3890},
        {"train": "Személyvonat", "departure": "14:32", "arrival": "18:10", "duration": "3h 38m", "price": 2100}
    ]
    res = format_search_results(results)
    
    assert "Elérhető vonatok:\n" in res
    assert "1. IC 503 — 14:05 > 16:55 (2h 50m) — 3 890 Ft" in res
    assert "2. Személyvonat — 14:32 > 18:10 (3h 38m) — 2 100 Ft" in res
    assert "Melyiket szeretnéd?" in res

def test_format_final_confirmation():
    offer = {
        "train": "IC 701",
        "departure": "16:05",
        "arrival": "18:55",
        "duration": "2h 50m",
        "price": 3890
    }
    res = format_final_confirmation(offer)
    
    assert "Vegso megerosites:\n" in res
    assert "Vonat:    IC 701" in res
    assert "Indulás:  16:05" in res
    assert "Érkezés:  18:55" in res
    assert "Menetidő: 2h 50m" in res
    assert "Ár:       3 890 Ft" in res
    assert "Biztosan fizetek? (igen / nem)" in res
