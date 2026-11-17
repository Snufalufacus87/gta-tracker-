"""
GTA VI Launch Countdown - a small, resizable Vice City sunset timer.

Made to sit on a second monitor: drag the window edges to any size and
everything scales with it. Right-click for size presets and "always on top".
Your window size, position and settings are remembered between launches.

Double-click this file to open it (Python 3 with Tkinter required),
or use one of the prebuilt executables from the GitHub Actions build.

Counts down to midnight, November 19, 2026, in your local time zone.
"""

import json
import math
import os
import random
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime

LAUNCH = datetime(2026, 11, 19, 0, 0, 0)  # local midnight

# Design size: everything is laid out for this, then scaled to the window.
BASE_W, BASE_H = 440, 200
DEFAULT_SIZE = (440, 200)
MIN_SIZE = (220, 100)
PRESETS = [("Tiny", 260, 118), ("Small", 340, 155), ("Medium", 440, 200),
           ("Large", 620, 282), ("Extra large", 820, 372)]
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".gta6_countdown.json")

# Vice City palette
SKY_STOPS = [
    (0.00, "#140a2e"),
    (0.30, "#3d1466"),
    (0.58, "#b02a8f"),
    (0.82, "#ff5e7e"),
    (1.00, "#ffb347"),
]
SEA_STOPS = [(0.0, "#5b1a6e"), (0.35, "#2a0f4a"), (1.0, "#0b0620")]
PINK = "#ff2fa6"
HOT_PINK = "#ff5fc4"
ORANGE = "#ffa53c"
CYAN = "#3ef2ff"
SILHOUETTE = "#12061f"


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c))) for c in rgb)


def lerp_color(c1, c2, t):
    a, b = hex_to_rgb(c1), hex_to_rgb(c2)
    return rgb_to_hex(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))


def gradient_at(stops, t):
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            return lerp_color(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 0)
    return stops[-1][1]


def pick_font(root, *candidates):
    available = {f.lower() for f in tkfont.families(root)}
    for name in candidates:
        if name.lower() in available:
            return name
    return "Helvetica"


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


class CountdownApp:
    def __init__(self, root):
        self.root = root
        root.title("GTA VI Countdown")
        root.configure(bg=SKY_STOPS[0][1])
        root.minsize(*MIN_SIZE)
        self._set_icon()

        settings = load_settings()
        geo = settings.get("geometry")
        root.geometry(geo if geo else "%dx%d" % DEFAULT_SIZE)
        self.on_top = tk.BooleanVar(value=settings.get("on_top", False))
        root.attributes("-topmost", self.on_top.get())

        self.display_font = pick_font(
            root, "Impact", "Anton", "Bebas Neue", "Haettenschweiler",
            "Arial Black", "DejaVu Sans Condensed", "Helvetica")
        self.label_font = pick_font(
            root, "Futura", "Century Gothic", "Segoe UI", "Avenir Next",
            "DejaVu Sans", "Helvetica")

        self.c = tk.Canvas(root, highlightthickness=0, bd=0, bg=SKY_STOPS[0][1])
        self.c.pack(fill="both", expand=True)

        self._build_menu()
        self.size = (0, 0)
        self.units = []
        self.stars = []
        self.status = None
        self._redraw_job = None
        self._tick_job = None

        self.c.bind("<Configure>", self._on_resize)
        self.c.bind("<Button-3>", self._show_menu)
        self.c.bind("<Button-2>", self._show_menu)          # macOS right-click
        self.c.bind("<Control-Button-1>", self._show_menu)  # macOS ctrl-click
        root.bind("<Escape>", lambda e: self._quit())
        root.protocol("WM_DELETE_WINDOW", self._quit)

        root.update_idletasks()
        self._redraw()
        self._tick()
        self._twinkle()

    # ---------- window plumbing ----------
    def _set_icon(self):
        try:
            size = 32
            img = tk.PhotoImage(width=size, height=size)
            for y in range(size):
                img.put(gradient_at(SKY_STOPS, y / (size - 1)), to=(0, y, size, y + 1))
            for y in range(8, 24):
                for x in range(size):
                    if (x - 16) ** 2 + (y - 22) ** 2 <= 100 and y % 4 != 3:
                        img.put(ORANGE if y < 16 else HOT_PINK, (x, y))
            self.root.iconphoto(True, img)
            self._icon = img
        except tk.TclError:
            pass

    def _build_menu(self):
        m = tk.Menu(self.root, tearoff=0)
        m.add_checkbutton(label="Always on top", variable=self.on_top,
                          command=self._apply_on_top)
        m.add_separator()
        for name, w, h in PRESETS:
            m.add_command(label=f"{name}  ({w}×{h})",
                          command=lambda w=w, h=h: self._set_size(w, h))
        m.add_separator()
        m.add_command(label="Close", command=self._quit)
        self.menu = m

    def _show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _apply_on_top(self):
        self.root.attributes("-topmost", self.on_top.get())

    def _set_size(self, w, h):
        self.root.geometry(f"{w}x{h}")

    def _quit(self):
        save_settings({"geometry": self.root.geometry(),
                       "on_top": self.on_top.get()})
        self.root.destroy()

    def _on_resize(self, event):
        if (event.width, event.height) == self.size:
            return
        if self._redraw_job:
            self.root.after_cancel(self._redraw_job)
        self._redraw_job = self.root.after(40, self._redraw)

    # ---------- drawing ----------
    def _redraw(self):
        self._redraw_job = None
        w = max(self.c.winfo_width(), MIN_SIZE[0])
        h = max(self.c.winfo_height(), MIN_SIZE[1])
        self.size = (w, h)
        self.w, self.h = w, h
        self.s = min(w / BASE_W, h / BASE_H)
        self.c.delete("all")
        self.stars = []
        self._draw_scene()
        self._draw_title()
        self._build_countdown()
        self._update_numbers()

    def _font(self, family, px, weight="normal"):
        return (family, -max(6, int(round(px))), weight)

    def _draw_scene(self):
        c, w, h, s = self.c, self.w, self.h, self.s
        horizon = int(h * 0.78)
        step = 2

        for y in range(0, horizon, step):
            c.create_rectangle(0, y, w, y + step, width=0,
                               fill=gradient_at(SKY_STOPS, y / horizon))

        rnd = random.Random(1986)
        for _ in range(int(40 * w / BASE_W)):
            x, y = rnd.uniform(0, w), rnd.uniform(0, horizon * 0.35)
            r = rnd.choice((0.6, 0.6, 0.9, 1.2)) * max(1, s)
            self.stars.append(c.create_oval(x - r, y - r, x + r, y + r,
                                            width=0, fill="#ffffff"))

        # Retro striped sun setting on the horizon
        cx, R = w / 2, h * 0.36
        cy = horizon + R * 0.08
        top = int(cy - R)
        for y in range(top, horizon):
            dy = y - cy
            if abs(dy) > R:
                continue
            t = (y - top) / (2 * R)
            if t > 0.22:
                period = max(4, 9 * s)
                gap = (1 + (t - 0.22) * 14) * s
                if (y - top) % period < gap:
                    continue
            half = math.sqrt(R * R - dy * dy)
            c.create_line(cx - half, y, cx + half, y,
                          fill=lerp_color("#fff27a", "#ff3d8b", min(1, t * 1.15)))

        # Skyline
        rnd = random.Random(7)
        x = 0.0
        while x < w:
            bw = rnd.uniform(8, 20) * s
            bh = rnd.uniform(4, 14) * s
            if w * 0.30 < x < w * 0.70:
                bh = rnd.uniform(10, 32) * s
            c.create_rectangle(x, horizon - bh, x + bw, horizon,
                               fill="#2a0c3d", width=0)
            if s >= 0.8:
                wy = horizon - bh + 3 * s
                while wy < horizon - 2 * s:
                    wx = x + 2 * s
                    while wx < x + bw - 2 * s:
                        if rnd.random() < 0.18:
                            c.create_rectangle(wx, wy, wx + s, wy + s, width=0,
                                               fill=rnd.choice((ORANGE, HOT_PINK, CYAN)))
                        wx += 4 * s
                    wy += 5 * s
            x += bw + rnd.uniform(0, 2) * s

        # Sea + shimmer
        for y in range(horizon, h, step):
            t = (y - horizon) / max(1, h - horizon)
            c.create_rectangle(0, y, w, y + step, width=0,
                               fill=gradient_at(SEA_STOPS, t))
        rnd = random.Random(42)
        row_gap = max(3, 4 * s)
        rows = int((h - horizon - 3) // row_gap)
        for i in range(rows):
            y = horizon + 3 + i * row_gap
            spread = R * (0.8 - 0.4 * i / max(1, rows))
            seg = rnd.uniform(10, 40) * s
            off = rnd.uniform(-spread, spread)
            c.create_line(cx + off - seg / 2, y, cx + off + seg / 2, y,
                          fill=lerp_color("#ffd36b", "#5b1a6e", i / max(1, rows)),
                          width=max(1, int(s)))
        c.create_line(0, horizon, w, horizon, fill="#ff8fb8")

        # Palms hug the window edges and scale with height
        ph = h * 0.95
        self._palm(w * 0.02, h + 4, ph, lean=0.45, scale=h / BASE_H * 0.55)
        self._palm(w * 0.98, h + 4, ph * 1.02, lean=-0.42, scale=h / BASE_H * 0.58)

    def _palm(self, bx, by, height, lean=0.4, scale=1.0):
        c = self.c
        tx, ty = bx + lean * height * 0.6, by - height
        ctrl_x, ctrl_y = bx + lean * height * 0.05, by - height * 0.55
        left, right = [], []
        steps = 20
        for i in range(steps + 1):
            t = i / steps
            x = (1 - t) ** 2 * bx + 2 * (1 - t) * t * ctrl_x + t * t * tx
            y = (1 - t) ** 2 * by + 2 * (1 - t) * t * ctrl_y + t * t * ty
            wd = (14 - 8 * t) * scale
            left.append((x - wd / 2, y))
            right.append((x + wd / 2, y))
        pts = left + right[::-1]
        c.create_polygon(*[v for p in pts for v in p], fill=SILHOUETTE, outline="")
        for a in (-170, -140, -110, -75, -40, -10, 20, 200, 160):
            self._frond(tx, ty, math.radians(a), 130 * scale, scale)
        c.create_oval(tx - 9 * scale, ty - 7 * scale, tx + 9 * scale, ty + 7 * scale,
                      fill=SILHOUETTE, outline="")

    def _frond(self, x0, y0, ang, length, scale):
        spine = []
        steps = 14
        for i in range(steps + 1):
            t = i / steps
            d = length * t
            spine.append((x0 + math.cos(ang) * d,
                          y0 + math.sin(ang) * d + (t ** 2) * length * 0.55))
        top, bot = [], []
        for i, (x, y) in enumerate(spine):
            t = i / steps
            wd = math.sin(math.pi * t) * 13 * scale * (1 - 0.3 * t)
            if i < steps:
                nx, ny = spine[i + 1]
            else:
                nx, ny = x + (x - spine[i - 1][0]), y + (y - spine[i - 1][1])
            dx, dy = nx - x, ny - y
            n = math.hypot(dx, dy) or 1
            px, py = -dy / n, dx / n
            top.append((x + px * wd, y + py * wd))
            bot.append((x - px * wd * 0.6, y - py * wd * 0.6))
        pts = top + bot[::-1]
        self.c.create_polygon(*[v for p in pts for v in p],
                              fill=SILHOUETTE, outline="", smooth=True)

    def _draw_title(self):
        c, w, h, s = self.c, self.w, self.h, self.s
        y = h * 0.5 - 70 * s
        size = 26 * s
        gta = self._font(self.display_font, size)
        vi = self._font(self.display_font, size * 1.25, "bold")
        gta_w = tkfont.Font(font=gta).measure("GTA ")
        vi_w = tkfont.Font(font=vi).measure("VI")
        x = w / 2 - (gta_w + vi_w) / 2
        c.create_text(x + 1, y + 1, text="GTA", font=gta, fill="#3a0d3f", anchor="w")
        c.create_text(x, y, text="GTA", font=gta, fill="#ffffff", anchor="w")
        vx = x + gta_w
        for d, col in ((3, "#5a1450"), (2, PINK)):
            d = max(1, d * s)
            for ox, oy in ((-d, 0), (d, 0), (0, -d), (0, d)):
                c.create_text(vx + ox, y + oy, text="VI", font=vi, fill=col, anchor="w")
        c.create_text(vx, y + 2 * s, text="VI", font=vi, fill=HOT_PINK, anchor="w")
        c.create_text(vx, y - 1.5 * s, text="VI", font=vi, fill="#ffe08a", anchor="w")
        c.create_text(vx, y, text="VI", font=vi, fill=ORANGE, anchor="w")

    def _build_countdown(self):
        c, w, h, s = self.c, self.w, self.h, self.s
        self.units = []
        box_w, box_h, gap = 82 * s, 66 * s, 14 * s
        total = 4 * box_w + 3 * gap
        x0 = (w - total) / 2
        y0 = h * 0.5 - 40 * s
        num_font = self._font(self.display_font, 38 * s)
        lab_font = self._font(self.label_font, 9 * s, "bold")
        labels = ["DAYS", "HRS", "MIN", "SEC"] if s < 0.85 else \
                 ["DAYS", "HOURS", "MINS", "SECS"]
        for i, lab in enumerate(labels):
            x = x0 + i * (box_w + gap)
            g = max(1, 3 * s)
            c.create_rectangle(x - g, y0 - g, x + box_w + g, y0 + box_h + g,
                               outline="#7a1f6c", width=1)
            c.create_rectangle(x, y0, x + box_w, y0 + box_h, fill="#1b0b30",
                               outline=HOT_PINK, width=max(1, int(round(1.5 * s))))
            c.create_rectangle(x + 2, y0 + 2, x + box_w - 1, y0 + box_h * 0.45,
                               fill="#24103d", width=0)
            ny = y0 + box_h * 0.43
            glow = c.create_text(x + box_w / 2 + 1.5 * s, ny + 1.5 * s, text="",
                                 font=num_font, fill="#7a1460")
            num = c.create_text(x + box_w / 2, ny, text="", font=num_font,
                                fill="#ffffff")
            c.create_text(x + box_w / 2, y0 + box_h - 9 * s, text=lab,
                          font=lab_font, fill=CYAN)
            self.units.append((glow, num))
            if i < 3:
                c.create_text(x + box_w + gap / 2, y0 + box_h * 0.42, text=":",
                              font=self._font(self.display_font, 26 * s, "bold"),
                              fill=HOT_PINK)

        sy = y0 + box_h + 15 * s
        sf = self._font(self.label_font, 10.5 * s, "bold")
        hide = s < 0.7  # too small to read; keep the tiny timer clean
        self.status_shadow = c.create_text(w / 2 + 1, sy + 1, text="", font=sf,
                                           fill="#3a0d3f",
                                           state="hidden" if hide else "normal")
        self.status = c.create_text(w / 2, sy, text="", font=sf, fill="#ffffff",
                                    state="hidden" if hide else "normal")

    # ---------- countdown logic ----------
    def _update_numbers(self):
        if not self.units:
            return 0
        remaining = (LAUNCH - datetime.now()).total_seconds()
        if remaining <= 0:
            vals, msg = (0, 0, 0, 0), "IT'S OUT. GO PLAY."
        else:
            secs = int(remaining)
            d, rem = divmod(secs, 86400)
            hh, rem = divmod(rem, 3600)
            m, sec = divmod(rem, 60)
            vals = (d, hh, m, sec)
            if d == 0:
                msg = "LAUNCH DAY • CLEAR YOUR SCHEDULE"
            elif d == 1:
                msg = "ONE MORE DAY • NOV 19, 2026"
            else:
                msg = f"{d} DAYS TO LEONIDA • NOV 19, 2026"
        for (glow, num), val in zip(self.units, vals):
            txt = f"{val:02d}"
            self.c.itemconfigure(glow, text=txt)
            self.c.itemconfigure(num, text=txt)
        self.c.itemconfigure(self.status, text=msg)
        self.c.itemconfigure(self.status_shadow, text=msg)
        return remaining

    def _tick(self):
        remaining = self._update_numbers()
        if remaining > 0:
            ms = int((remaining - int(remaining)) * 1000) + 15
        else:
            ms = 1000
        self._tick_job = self.root.after(max(50, ms), self._tick)

    def _twinkle(self):
        if self.stars:
            for st in random.sample(self.stars, min(5, len(self.stars))):
                self.c.itemconfigure(st, fill=random.choice(
                    ("#ffffff", "#ffd6f0", "#b9a4ff", "#5a3a8a")))
        self.root.after(450, self._twinkle)


def main():
    root = tk.Tk()
    CountdownApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
