#!/usr/bin/env python3
import argparse
import os
import time
import sys

from config import PATH_POLL_INTERVAL, WEATHER_POLL_INTERVAL, STATION, DIRECTION
from path_client import get_arrivals
from path_signalr import PathRealtime
from weather_client import get_weather
from display import MatrixDisplay


def main():
    parser = argparse.ArgumentParser(description="PATH Train LED Matrix Display")
    parser.add_argument("--station", default=STATION, help=f"Station code (default from config.py: {STATION})")
    parser.add_argument("--direction", default=DIRECTION, help=f"Direction: ToNY or ToNJ (default from config.py: {DIRECTION})")
    parser.add_argument("--led-gpio-mapping", default="adafruit-hat")
    parser.add_argument("--led-slowdown-gpio", type=int, default=4)
    parser.add_argument(
        "--font-path",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "6x9.bdf"),
        help="Path to BDF font file for matrix display",
    )
    args = parser.parse_args()

    display = MatrixDisplay(args)
    print(f"Showing {args.direction} trains from {args.station}")

    # Primary source: the RidePATH app's live SignalR feed (if configured in
    # config.py). Runs in the background and caches the latest arrivals.
    realtime = PathRealtime(args.station, args.direction)
    realtime.start()

    arrivals = []
    last_updated = ""
    weather = None
    last_json_poll = 0.0
    last_weather_poll = 0.0
    last_source = None

    # On startup, give the live SignalR feed a moment to connect before falling
    # back to ridepath.json, so the primary source is live from the first frame
    # rather than briefly showing the JSON fallback during the handshake.
    STARTUP_GRACE = 10.0
    started = time.monotonic()

    try:
        while True:
            now = time.time()

            # --- PATH data: SignalR primary (cheap cache read), JSON fallback ---
            rt_arrivals, rt_updated = realtime.latest()
            if rt_arrivals:
                arrivals, last_updated = rt_arrivals, rt_updated
                if last_source != "signalr":
                    print("PATH source: live SignalR feed", flush=True)
                    last_source = "signalr"
            elif time.monotonic() - started >= STARTUP_GRACE and (
                now - last_json_poll >= PATH_POLL_INTERVAL or last_source is None
            ):
                # Live feed isn't up after the grace window — use the JSON feed.
                try:
                    arrivals, last_updated = get_arrivals(args.station, args.direction)
                    if last_source != "json":
                        print("PATH source: ridepath.json (fallback)", flush=True)
                        last_source = "json"
                except Exception as e:
                    print(f"PATH error: {e}", file=sys.stderr)
                last_json_poll = now

            if now - last_weather_poll >= WEATHER_POLL_INTERVAL:
                try:
                    weather = get_weather()
                except Exception as e:
                    print(f"Weather error: {e}", file=sys.stderr)
                last_weather_poll = now

            display.render(arrivals, last_updated, weather)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
