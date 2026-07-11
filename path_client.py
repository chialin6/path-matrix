#!/usr/bin/env python3
import requests
from dataclasses import dataclass

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


def _hex_to_rgb(hex_str: str) -> tuple:
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


@dataclass
class Arrival:
    headsign: str
    minutes_list: list
    color: tuple

    @property
    def abbreviated(self) -> str:
        return ABBREVIATIONS.get(self.headsign, self.headsign[:4])

    @property
    def next_minutes(self) -> int:
        return self.minutes_list[0] if self.minutes_list else 999

    @property
    def times_str(self) -> str:
        return " ".join(str(m) for m in self.minutes_list)


def get_arrivals(station_code: str, direction: str = "ToNY", max_per_dest: int = 3) -> list:
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

    by_dest = {}
    for msg in dir_data["messages"]:
        headsign = msg["headSign"]
        minutes = max(0, int(msg["secondsToArrival"]) // 60)
        color = _hex_to_rgb(msg["lineColor"])

        if headsign not in by_dest:
            by_dest[headsign] = {"minutes": [], "color": color}
        if len(by_dest[headsign]["minutes"]) < max_per_dest:
            by_dest[headsign]["minutes"].append(minutes)

    arrivals = [
        Arrival(headsign=k, minutes_list=v["minutes"], color=v["color"])
        for k, v in by_dest.items()
    ]
    arrivals.sort(key=lambda a: a.next_minutes)
    return arrivals


if __name__ == "__main__":
    import sys

    station = sys.argv[1] if len(sys.argv) > 1 else "GRV"
    direction = sys.argv[2] if len(sys.argv) > 2 else "ToNY"
    arrivals = get_arrivals(station, direction)
    for a in arrivals:
        r, g, b = a.color
        print(f"\033[38;2;{r};{g};{b}m●\033[0m {a.abbreviated:<6} {a.times_str}")
