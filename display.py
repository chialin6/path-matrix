#!/usr/bin/env python3
import os

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics as rgb_graphics
    HAS_MATRIX = True
except ImportError:
    HAS_MATRIX = False

ANSI_RESET = "\033[0m"


def _ansi_fg(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"


class MatrixDisplay:
    def __init__(self, args):
        self.args = args
        self.matrix = None
        self.font = None
        self.canvas = None

        if HAS_MATRIX:
            self._init_matrix()

    def _init_matrix(self):
        options = RGBMatrixOptions()
        options.hardware_mapping = self.args.led_gpio_mapping
        options.rows = self.args.led_rows
        options.cols = self.args.led_cols
        options.gpio_slowdown = self.args.led_slowdown_gpio
        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()

        self.font = rgb_graphics.Font()
        self.font.LoadFont(self.args.font_path)

    def render(self, arrivals):
        if HAS_MATRIX:
            self._render_matrix(arrivals)
        else:
            self._render_terminal(arrivals)

    def _render_matrix(self, arrivals):
        self.canvas.Clear()

        # Layout constants for 64x32 display with 5x8 font
        row_baselines = [10, 26]  # y baselines for rows 1 and 2
        dot_x = 1
        dot_size = 3
        text_x = 6   # x start for destination abbreviation
        times_x = 32  # fixed x column for arrival times

        white = rgb_graphics.Color(255, 255, 255)

        for i, arrival in enumerate(arrivals[:2]):
            y = row_baselines[i]
            r, g, b = arrival.color

            # Draw colored 3x3 dot, vertically centered near text baseline
            dot_y_top = y - dot_size - 1
            for dy in range(dot_size):
                for dx in range(dot_size):
                    self.canvas.SetPixel(dot_x + dx, dot_y_top + dy, r, g, b)

            # Draw destination abbreviation
            rgb_graphics.DrawText(self.canvas, self.font, text_x, y, white, arrival.abbreviated)

            # Draw arrival times at fixed column
            rgb_graphics.DrawText(self.canvas, self.font, times_x, y, white, arrival.times_str)

        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def _render_terminal(self, arrivals):
        print("\033[H\033[J", end="")  # clear screen
        print("PATH Arrivals  (Ctrl+C to stop)")
        print("─" * 30)

        if not arrivals:
            print("No trains found")
            return

        for arrival in arrivals[:2]:
            r, g, b = arrival.color
            dot = f"{_ansi_fg(r, g, b)}●{ANSI_RESET}"
            print(f"{dot} {arrival.abbreviated:<6} {arrival.times_str}")
