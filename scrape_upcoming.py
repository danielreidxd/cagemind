"""
Scraper de eventos próximos de UFCStats.com.
Extrae carteleras confirmadas y genera predicciones.

Uso:
    python scrape_upcoming.py
"""
from __future__ import annotations

import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup

OUTPUT_FILE = Path("data/raw/ufcstats/upcoming_events.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def clean(text):
    if not text:
        return ""
    return " ".join(text.strip().split())


def scrape_upcoming_list():
    """Scrapea la lista de eventos upcoming."""
    url = "http://www.ufcstats.com/statistics/events/upcoming"
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "lxml")

    events = []
    table = soup.find("table", class_="b-statistics__table-events")
    if not table:
        return events

    tbody = table.find("tbody")
    if not tbody:
        return events

    rows = tbody.find_all("tr", class_="b-statistics__table-row")
    for row in rows:
        link = row.find("a", class_="b-link")
        if not link:
            continue

        name = clean(link.text)
        href = link.get("href", "").strip()
        date_span = row.find("span", class_="b-statistics__date")
        date = clean(date_span.text) if date_span else None

        tds = row.find_all("td")
        location = clean(tds[-1].text) if len(tds) > 1 else None

        if name and href:
            events.append({
                "name": name,
                "date": date,
                "url": href,
                "location": location,
            })

    return events


def scrape_event_fights(event_url):
    """Scrapea las peleas de un evento."""
    r = requests.get(event_url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "lxml")

    fights = []
    rows = soup.find_all("tr", class_="b-fight-details__table-row")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        # Peleadores
        fighters_col = cols[1]
        fighter_links = fighters_col.find_all("a")
        if len(fighter_links) >= 2:
            fa = clean(fighter_links[0].text)
            fb = clean(fighter_links[1].text)
        else:
            fps = fighters_col.find_all("p")
            if len(fps) >= 2:
                fa = clean(fps[0].text)
                fb = clean(fps[1].text)
            else:
                continue

        if not fa or not fb:
            continue

        # Weight class
        wc = None
        if len(cols) > 6:
            wc = clean(cols[6].text)
        if not wc:
            for col in cols:
                txt = clean(col.text)
                if "weight" in txt.lower() or "bout" in txt.lower():
                    wc = txt
                    break

        fights.append({
            "fighter_a": fa,
            "fighter_b": fb,
            "weight_class": wc if wc else None,
        })

    return fights


def main():
    print("=" * 60)
    print("SCRAPING UPCOMING UFC EVENTS")
    print("=" * 60)

    print("\nObteniendo lista de eventos...")
    events = scrape_upcoming_list()
    print("Eventos encontrados: " + str(len(events)))

    for event in events:
        print("\n  " + event["name"] + " | " + str(event["date"]))
        fights = scrape_event_fights(event["url"])
        event["fights"] = fights
        print("    Peleas: " + str(len(fights)))
        for f in fights[:3]:
            print("      " + f["fighter_a"] + " vs " + f["fighter_b"])
        if len(fights) > 3:
            print("      ... +" + str(len(fights) - 3) + " mas")

    # Guardar
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

    total_fights = sum(len(e.get("fights", [])) for e in events)
    print("\n" + "=" * 60)
    print("COMPLETADO: " + str(len(events)) + " eventos, " + str(total_fights) + " peleas")
    print("Guardado en: " + str(OUTPUT_FILE))
    print("=" * 60)


if __name__ == "__main__":
    main()
