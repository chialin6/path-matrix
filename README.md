# PATH Train + Weather LED Matrix Display

Shows live PATH train arrivals and a rotating weather ticker (feels-like
temp, rain forecast, last-updated time) on a 64x32 RGB LED matrix driven by
a Raspberry Pi. Falls back to a terminal preview if the `rgbmatrix` library
isn't installed, so you can develop/test on a regular machine.

## Setup

1. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
   On the Pi, also install [rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix)
   (provides the `rgbmatrix` Python bindings) following its own build
   instructions.

2. Create your local config from the template:
   ```
   cp config.py.example config.py
   ```
   `config.py` is gitignored — it's never committed, so your station and
   location stay local to your Pi.

3. Edit `config.py`:
   - `STATION` — your PATH station code (e.g. `GRV` for Grove Street, `HOB`
     for Hoboken, `WTC`, `JSQ`, `NWK`, `23S`/`14S`/`09S`, `33S`, `CHR`). Run
     `python3 path_client.py <STATION> <ToNY|ToNJ>` to sanity-check a code
     against the live API.
   - `DIRECTION` — `ToNY` or `ToNJ`.
   - `WEATHER_LAT` / `WEATHER_LON` — coordinates for the weather forecast.
     Get these from Google Maps (right-click a location -> "What's here?").
   - The remaining values (poll intervals, rain threshold, ticker speed)
     have sensible defaults but are tweakable.

## Running

```
python3 main.py
```

Useful flags (override `config.py` for a one-off run):
- `--station` / `--direction` — override the station/direction from config.
- `--led-gpio-mapping` — matrix hardware mapping (default `adafruit-hat`).
- `--led-slowdown-gpio` — GPIO slowdown factor (default `4`; raise if you
  see flicker).
- `--font-path` — path to a custom BDF font for the arrival rows.

Without a matrix attached (e.g. on a laptop), it renders to the terminal
instead.

## Running as a service (Raspberry Pi)

The provided `path_display.service` template is filled in and installed
automatically:

```
./install_service.sh
sudo systemctl start path_display.service
```

This detects the repo path and writes the unit to
`/etc/systemd/system/path_display.service`, enabling it to start on boot.
Logs are viewable with `journalctl -u path_display.service -f`.

## Fonts

`fonts/4x6.bdf` (header ticker) and `fonts/6x9.bdf` (arrival rows) are
committed to the repo — no separate download needed.
