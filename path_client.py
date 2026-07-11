#!/usr/bin/env python3
import requests
from dataclasses import dataclass, field

API_URL = "https://www.panynj.gov/bin/portauthority/ridepath.json"

ABBREVIATIONS = {
    "33rd Street": "33St",
    "World Trade Center": "WTC",
    "Journal Square": "JSQ",
    "Newark": "Nwk",
    "Hoboken": "HOB",
    "Christopher Street": "Chr",
    "9th Street": "9St",
    "14th Street": "14St",
    "23rd Street": "23St",
}

# Abbreviate API message strings to fit the display
MESSAGE_ABBREV = {
    "Arriving": "Now",
    "Boarding": "Now",
}


def _hex_to_rgb(hex_str: str) -> tuple:
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


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
    color: tuple
    seconds_list: list = field(default_factory=list)
    message_list: list = field(default_factory=list)

    @property
    def abbreviated(self) -> str:
        return ABBREVIATIONS.get(self.headsign, self.headsign[:4])

    @property
    def next_seconds(self) -> int:
        return self.seconds_list[0] if self.seconds_list else 999999

    def times_message(self) -> str:
        return " ".join(_abbrev_message(m) for m in self.message_list)

    def times_mmss(self) -> str:
        return " ".join(_mmss(s) for s in self.seconds_list)

    def times_minutes(self) -> str:
        return " ".join(str(max(0, s) // 60) for s in self.seconds_list)


def get_arrivals(station_code: str, direction: str = "ToNY", max_trains: int = 2) -> list:
    resp = requests.get(API_URL, timeout=8)
    resp.raise_for_status()
    data = resp.json()

    station_data = next(
        (r for r in data["results"] if r["consideredStation"] == station_code),
        None,
    )
    if not station_data:
        return []

    dir_data = next(
        (d for d in station_data["destinations"] if d["label"] == direction),
        None,
    )
    if not dir_data:
        return []

    # One row per train, already sorted by arrival time from the API
    arrivals = []
    for msg in dir_data["messages"][:max_trains]:
        arrivals.append(Arrival(
            headsign=msg["headSign"],
            color=_hex_to_rgb(msg["lineColor"]),
            seconds_list=[max(0, int(msg["secondsToArrival"]))],
            message_list=[msg["arrivalTimeMessage"]],
        ))
    return arrivals


if __name__ == "__main__":
    import sys

    station = sys.argv[1] if len(sys.argv) > 1 else "GRV"
    direction = sys.argv[2] if len(sys.argv) > 2 else "ToNY"
    arrivals = get_arrivals(station, direction)
    for a in arrivals:
        r, g, b = a.color
        print(
            f"\033[38;2;{r};{g};{b}m●\033[0m {a.abbreviated:<6}"
            f"  msg={a.times_message():<8}  mmss={a.times_mmss()}"
        )
