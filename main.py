#!/usr/bin/env python3
import argparse
import os
import time
import sys

from path_client import get_arrivals
from display import MatrixDisplay


def main():
    parser = argparse.ArgumentParser(description="PATH Train LED Matrix Display")
    parser.add_argument("--station", default="GRV", help="Station code (default: GRV = Grove Street)")
    parser.add_argument("--direction", default="ToNY", help="Direction: ToNY or ToNJ (default: ToNY)")
    parser.add_argument("--led-gpio-mapping", default="adafruit-hat")
    parser.add_argument("--led-rows", type=int, default=32)
    parser.add_argument("--led-cols", type=int, default=64)
    parser.add_argument("--led-slowdown-gpio", type=int, default=4)
    parser.add_argument(
        "--font-path",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "6x9.bdf"),
        help="Path to BDF font file for matrix display",
    )
    args = parser.parse_args()

    display = MatrixDisplay(args)
    print(f"Showing {args.direction} trains from {args.station} — refreshing every 20s")

    try:
        while True:
            try:
                arrivals, last_updated = get_arrivals(args.station, args.direction)
                display.render(arrivals, last_updated)
            except Exception as e:
                print(f"Error fetching arrivals: {e}", file=sys.stderr)
            time.sleep(20)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
