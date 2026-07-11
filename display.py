#!/usr/bin/env python3
import os

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics as rgb_graphics
    HAS_MATRIX = True
except ImportError:
    HAS_MATRIX = False

ANSI_RESET = "\033[0m"
ANSI_DIM = "\033[2m"

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

MATRIX_WIDTH = 64
MATRIX_HEIGHT = 32
TIME_RIGHT_PADDING = 2  # px gap between time text and right edge


def _ansi_fg(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"



def _draw_circle(canvas, cx, cy, radius, colors):
    """Draw a filled circle. Two colors = left/right split for combined routes."""
    c1 = colors[0]
    c2 = colors[1] if len(colors) > 1 else None
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                r, g, b = c2 if (c2 is not None and dx >= 0) else c1
                canvas.SetPixel(cx + dx, cy + dy, r, g, b)


class MatrixDisplay:
    def __init__(self, args):
        self.args = args
        self.matrix = None
        self.font = None        # 6x9 for arrival rows
        self.font_small = None  # 4x6 for header
        self.canvas = None

        self._last_updated = ""

        if HAS_MATRIX:
            self._init_matrix()

    def _init_matrix(self):
        # Load fonts before RGBMatrix init: the library drops root privileges
        # to uid=daemon after hardware setup, losing access to /home/chialin6/.
        font_path = getattr(self.args, 'font_path',
                            os.path.join(FONTS_DIR, "6x9.bdf"))
        self.font = rgb_graphics.Font()
        self.font.LoadFont(font_path)

        self.font_small = rgb_graphics.Font()
        self.font_small.LoadFont(os.path.join(FONTS_DIR, "4x6.bdf"))

        options = RGBMatrixOptions()
        options.hardware_mapping = self.args.led_gpio_mapping
        options.rows = MATRIX_HEIGHT
        options.cols = MATRIX_WIDTH
        options.gpio_slowdown = self.args.led_slowdown_gpio
        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()

    def render(self, arrivals, last_updated=""):
        if last_updated:
            self._last_updated = last_updated
        if HAS_MATRIX:
            self._render_matrix(arrivals)
        else:
            self._render_terminal(arrivals)

    def _render_matrix(self, arrivals):
        self.canvas.Clear()

        white = rgb_graphics.Color(255, 255, 255)
        grey = rgb_graphics.Color(110, 110, 110)

        # Header row: small grey text at top using 4x6 font
        if self._last_updated:
            rgb_graphics.DrawText(self.canvas, self.font_small, 1, 6, grey, f"updated @ {self._last_updated}")

        # Two arrival rows using 6x9 font
        # Layout: circle dot (radius 3) + gap + name + times at fixed col
        dot_radius = 3
        dot_cx = 4        # circle center x (1px left padding from edge)
        text_x = 11       # text starts after dot + 1px extra gap
        row_baselines = [17, 28]

        for i, arrival in enumerate(arrivals[:2]):
            y = row_baselines[i]
            r, g, b = arrival.color

            # Circle dot centered vertically on the text
            dot_cy = y - 3
            _draw_circle(self.canvas, dot_cx, dot_cy, dot_radius, arrival.colors)

            # Destination abbreviation
            rgb_graphics.DrawText(self.canvas, self.font, text_x, y, white, arrival.abbreviated)

            # Arrival times — right-aligned to the matrix edge
            time_str = arrival.times_message()
            time_x = MATRIX_WIDTH - len(time_str) * 6 - TIME_RIGHT_PADDING
            rgb_graphics.DrawText(self.canvas, self.font, time_x, y, white, time_str)

        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def _render_terminal(self, arrivals):
        print("\033[H\033[J", end="")
        if self._last_updated:
            print(f"{ANSI_DIM}updated @ {self._last_updated}{ANSI_RESET}")
        print("─" * 30)

        if not arrivals:
            print("No trains found")
            return

        for arrival in arrivals[:2]:
            if len(arrival.colors) > 1:
                r1, g1, b1 = arrival.colors[0]
                r2, g2, b2 = arrival.colors[1]
                dot = f"{_ansi_fg(r1,g1,b1)}◐{ANSI_RESET}{_ansi_fg(r2,g2,b2)}◑{ANSI_RESET}"
            else:
                r, g, b = arrival.color
                dot = f"{_ansi_fg(r, g, b)}●{ANSI_RESET}"
            print(f"{dot} {arrival.abbreviated:<5} {arrival.times_message():>3}")
