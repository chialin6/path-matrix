#!/usr/bin/env python3
"""Live PATH arrivals via the RidePATH app's SignalR feed.

Used as a fallback when the public ridepath.json feed returns nothing. Runs a
background thread that holds a SignalR connection to PANYNJ's realtime hub and
caches the latest arrivals, so the display loop can read them synchronously.

Secrets/flow recovered by decompiling the RidePATH 6.2.2 Android app
(see the project memory note "RidePATH feed & app key"). The hardcoded token
broker URL + bearer may rotate on app updates; re-extract from a newer APK if
this stops returning 200.
"""
import json
import threading
import time
import uuid
import logging
from datetime import datetime, timezone

import requests

from path_client import Arrival, _parse_colors, _parse_last_updated

# --- token broker secrets (app's bf.a / bf.b) live in config.py, which is
# gitignored, so no credentials are committed. If they're absent, this module
# stays dormant and the caller falls back to the public JSON feed. ---
try:
    from config import SIGNALR_TOKEN_BROKER as _TOKEN_BROKER
    from config import SIGNALR_BEARER as _BEARER
except Exception:
    _TOKEN_BROKER = None
    _BEARER = None

# Pi station/direction codes -> the strings the token broker expects
_STATION_NAME = {
    "NWK": "Newark", "HAR": "Harrison", "JSQ": "Journal Square",
    "GRV": "Grove Street", "EXP": "Exchange Place", "NEW": "Newport",
    "HOB": "Hoboken", "WTC": "World Trade Center", "CHR": "Christopher Street",
    "09S": "9th Street", "14S": "14th Street", "23S": "23rd Street",
    "33S": "33rd Street",
}
_DIRECTION_NAME = {"ToNY": "New York", "ToNJ": "New Jersey"}

# destination headsign -> target code, so Arrival.abbreviated works like the JSON feed
_HEADSIGN_TO_TARGET = {
    "33rd Street": "33S", "World Trade Center": "WTC", "Journal Square": "JSQ",
    "Hoboken": "HOB", "Newark": "NWK", "Harrison": "HAR", "Exchange Place": "EXP",
    "Newport": "NEW", "Grove Street": "GRV", "Christopher Street": "CHR",
    "9th Street": "09S", "14th Street": "14S", "23rd Street": "23S",
    "Hoboken via": "HOB",
}

# Data older than this (seconds) is treated as stale and not returned.
_STALE_AFTER = 30.0


def _app_headers():
    return {
        "Authorization": f"Bearer {_BEARER}",
        "Content-Type": "application/json",
        "AppName": "RidePATH", "AppVersion": "6.2.2", "Platform": "Android",
        "AppInstallId": str(uuid.uuid4()),
        "RequestId": str(uuid.uuid4()),
        "DeviceTime": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        "User-Agent": "okhttp/4.9.2",
    }


class PathRealtime:
    """Background SignalR subscriber for one (station, direction)."""

    def __init__(self, station_code: str, direction_code: str = "ToNY", max_trains: int = 2):
        self.station_code = station_code
        self.direction_code = direction_code
        self.max_trains = max_trains
        self.station_name = _STATION_NAME.get(station_code, station_code)
        self.direction_name = _DIRECTION_NAME.get(direction_code, direction_code)
        self._lock = threading.Lock()
        self._arrivals = []
        self._last_msg_ts = 0.0          # monotonic time of last message
        self._last_updated_str = ""
        self._stop = threading.Event()
        self._thread = None

    # ---- public API ----
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="path-signalr", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def latest(self):
        """Return (list[Arrival], last_updated_str). Empty if stale or no data yet."""
        with self._lock:
            if not self._arrivals or (time.monotonic() - self._last_msg_ts) > _STALE_AFTER:
                return [], ""
            return list(self._arrivals), self._last_updated_str

    def is_fresh(self):
        with self._lock:
            return bool(self._arrivals) and (time.monotonic() - self._last_msg_ts) <= _STALE_AFTER

    # ---- internals ----
    def _get_token(self):
        if not (_TOKEN_BROKER and _BEARER):
            return None, None
        body = {"station": self.station_name, "direction": self.direction_name}
        r = requests.post(_TOKEN_BROKER, headers=_app_headers(), data=json.dumps(body), timeout=20)
        if r.status_code != 200 or not r.content:
            return None, None
        tok = r.json()
        return (tok.get("Url") or tok.get("url"), tok.get("AccessToken") or tok.get("accessToken"))

    def _on_message(self, args):
        try:
            # args = ["<connid>,ToNY,GRV", "<json>"]
            payload = json.loads(args[1]) if len(args) > 1 else None
            if not payload:
                return
            arrivals = []
            last_updated = ""
            for m in payload.get("messages", [])[: self.max_trains]:
                headsign = m.get("headSign", "")
                target = _HEADSIGN_TO_TARGET.get(headsign, "")
                arrivals.append(Arrival(
                    headsign=headsign,
                    target=target,
                    colors=_parse_colors(m.get("lineColor", "#FFFFFF")),
                    seconds_list=[max(0, int(float(m.get("secondsToArrival", 0))))],
                    message_list=[m.get("arrivalTimeMessage", "")],
                ))
                if not last_updated:
                    last_updated = _parse_last_updated(m.get("lastUpdated", ""))
            with self._lock:
                self._arrivals = arrivals
                self._last_updated_str = last_updated
                self._last_msg_ts = time.monotonic()
        except Exception as e:  # never let a bad message kill the thread
            logging.debug("signalr message parse error: %s", e)

    def _run(self):
        from signalrcore.hub_connection_builder import HubConnectionBuilder
        backoff = 2
        while not self._stop.is_set():
            try:
                url, access = self._get_token()
                if not (url and access):
                    time.sleep(min(backoff, 30)); backoff = min(backoff * 2, 30); continue
                hub = (HubConnectionBuilder()
                       .with_url(url, options={"access_token_factory": lambda a=access: a})
                       .build())
                connected = threading.Event()
                closed = threading.Event()
                hub.on("SendMessage", self._on_message)
                hub.on_open(lambda: connected.set())
                hub.on_close(lambda: closed.set())
                hub.on_error(lambda e: logging.debug("signalr error: %s", e))
                hub.start()
                backoff = 2
                # Stay connected; the token JWT expires, so recycle periodically.
                deadline = time.monotonic() + 600  # refresh token every ~10 min
                while not self._stop.is_set() and not closed.is_set() and time.monotonic() < deadline:
                    time.sleep(1)
                try:
                    hub.stop()
                except Exception:
                    pass
            except Exception as e:
                logging.debug("signalr connect error: %s", e)
                time.sleep(min(backoff, 30)); backoff = min(backoff * 2, 30)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("SignalRCoreClient").setLevel(logging.CRITICAL)
    st = sys.argv[1] if len(sys.argv) > 1 else "GRV"
    di = sys.argv[2] if len(sys.argv) > 2 else "ToNY"
    rt = PathRealtime(st, di)
    rt.start()
    print(f"Subscribing to {st} {di} via SignalR; waiting for data...")
    for _ in range(30):
        time.sleep(2)
        arrivals, lu = rt.latest()
        if arrivals:
            print(f"[{lu}] " + "  ".join(f"{a.abbreviated}:{a.times_message()}" for a in arrivals))
    rt.stop()
