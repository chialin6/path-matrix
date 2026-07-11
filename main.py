#!/usr/bin/env python3
import argparse
import os
import time
import sys

from config import PATH_POLL_INTERVAL, WEATHER_POLL_INTERVAL
from path_client import get_arrivals
from weather_client import get_weather
from display import MatrixDisplay


def main():
    parser = argparse.ArgumentParser(description="PATH Train LED Matrix Display")
    parser.add_argument("--station", default="GRV", help="Station code (default: GRV = Grove Street)")
    parser.add_argument("--direction", default="ToNY", help="Direction: ToNY or ToNJ (default: ToNY)")
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

    arrivals = []
    last_updated = ""
    weather = None
    last_path_poll = 0
    last_weather_poll = 0

    try:
        while True:
            now = time.time()

            if now - last_path_poll >= PATH_POLL_INTERVAL:
                try:
                    arrivals, last_updated = get_arrivals(args.station, args.direction)
                except Exception as e:
                    print(f"PATH error: {e}", file=sys.stderr)
                last_path_poll = now

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
