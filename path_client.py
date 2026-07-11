#!/usr/bin/env python3
import requests
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

_NY_TZ = ZoneInfo("America/New_York")

API_URL = "https://www.panynj.gov/bin/portauthority/ridepath.json"

# Keyed on API `target` code — more stable than headsign which varies by route
TARGET_ABBREVIATIONS = {
    "33S": "33St",
    "WTC": "WTC",
    "JSQ": "JSQ",
    "NWK": "Newark",
    "HOB": "HOB",
    "CHR": "Chr St",
    "09S": "9St",
    "14S": "14St",
    "23S": "23St",
    "NEW": "Newark",
    "HAR": "HARRSN",
    "EXP": "EXC PL",
}

# Abbreviate API message strings to fit the display
MESSAGE_ABBREV = {
    "Arriving": "Now",
    "Boarding": "Now",
}


def _hex_to_rgb(hex_str: str) -> tuple:
    h = hex_str.strip().lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _parse_colors(line_color: str) -> list:
    return [_hex_to_rgb(c) for c in line_color.split(",")]


def _mmss(seconds: int) -> str:
    seconds = max(0, seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def _abbrev_message(msg: str) -> str:
    """Shorten API message strings: '4 min' -> '4m', 'Arriving' -> 'Now'."""
    if msg in MESSAGE_ABBREV:
        return MESSAGE_ABBREV[msg]
    if msg.endswith(" min"):
        return msg[: -len(" min")] + "m"
    return msg


@dataclass
class Arrival:
    headsign: str
    target: str
    colors: list  # list of (r,g,b); two entries means a combined route
    seconds_list: list = field(default_factory=list)
    message_list: list = field(default_factory=list)

    @property
    def color(self) -> tuple:
        return self.colors[0]

    @property
    def abbreviated(self) -> str:
        return TARGET_ABBREVIATIONS.get(self.target, self.headsign[:4])

    @property
    def next_seconds(self) -> int:
        return self.seconds_list[0] if self.seconds_list else 999999

    def times_message(self) -> str:
        return " ".join(_abbrev_message(m) for m in self.message_list)

    def times_mmss(self) -> str:
        return " ".join(_mmss(s) for s in self.seconds_list)

    def times_minutes(self) -> str:
        return " ".join(str(max(0, s) // 60) for s in self.seconds_list)


def _parse_last_updated(ts: str) -> str:
    """Parse ISO 8601 timestamp and return HH:MM in New York time."""
    try:
        return datetime.fromisoformat(ts).astimezone(_NY_TZ).strftime("%H:%M")
    except Exception:
        return ""


def get_arrivals(station_code: str, direction: str = "ToNY", max_trains: int = 2):
    """Return (list[Arrival], last_updated_str) where last_updated_str is 'HH:MM' or ''."""
    resp = requests.get(API_URL, timeout=8)
    resp.raise_for_status()
    data = resp.json()

    station_data = next(
        (r for r in data["results"] if r["consideredStation"] == station_code),
        None,
    )
    if not station_data:
        return [], ""

    dir_data = next(
        (d for d in station_data["destinations"] if d["label"] == direction),
        None,
    )
    if not dir_data:
        return [], ""

    # One row per train, already sorted by arrival time from the API
    arrivals = []
    last_updated = ""
    for msg in dir_data["messages"][:max_trains]:
        arrivals.append(Arrival(
            headsign=msg["headSign"],
            target=msg["target"],
            colors=_parse_colors(msg["lineColor"]),
            seconds_list=[max(0, int(msg["secondsToArrival"]))],
            message_list=[msg["arrivalTimeMessage"]],
        ))
        if not last_updated:
            last_updated = _parse_last_updated(msg.get("lastUpdated", ""))
    return arrivals, last_updated


if __name__ == "__main__":
    import sys

    station = sys.argv[1] if len(sys.argv) > 1 else "GRV"
    direction = sys.argv[2] if len(sys.argv) > 2 else "ToNY"
    arrivals, last_updated = get_arrivals(station, direction)
    print(f"Last updated: {last_updated}")
    for a in arrivals:
        r, g, b = a.color
        print(
            f"\033[38;2;{r};{g};{b}m●\033[0m {a.abbreviated:<6}"
            f"  msg={a.times_message():<8}  mmss={a.times_mmss()}"
        )
