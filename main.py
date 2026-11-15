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
    captured = None          # time.monotonic() when `arrivals` was captured
    weather = None
    last_json_poll = 0.0
    last_weather_poll = 0.0
    last_source = None

    # Render often so the countdown ticks smoothly; display.render only pushes a
    # new frame to the panel when the shown value actually changes (no wasteful
    # refresh). Data reads are cheap: SignalR is an in-memory cache read, and
    # ridepath.json is still only polled every PATH_POLL_INTERVAL.
    RENDER_INTERVAL = 0.25

    try:
        while True:
            now = time.time()

            # --- PATH data: SignalR primary (cheap cache read), JSON fallback ---
            rt_arrivals, rt_updated, rt_captured = realtime.snapshot()
            if rt_arrivals:
                arrivals, last_updated, captured = rt_arrivals, rt_updated, rt_captured
                if last_source != "signalr":
                    print("PATH source: live SignalR feed", flush=True)
                    last_source = "signalr"
            elif now - last_json_poll >= PATH_POLL_INTERVAL or captured is None:
                try:
                    arrivals, last_updated = get_arrivals(args.station, args.direction)
                    captured = time.monotonic()
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

            elapsed = (time.monotonic() - captured) if captured is not None else 0.0
            display.render(arrivals, last_updated, weather, elapsed=elapsed)
            time.sleep(RENDER_INTERVAL)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
