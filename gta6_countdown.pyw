"""
GTA VI Launch Countdown - a Vice City sunset desktop window.

Double-click this file to open it (Python 3 with Tkinter required),
or use one of the prebuilt executables from the GitHub Actions build.

Counts down to midnight, November 19, 2026, in your local time zone.
"""

import math
import random
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime

LAUNCH = datetime(2026, 11, 19, 0, 0, 0)  # local midnight
W, H = 960, 600
HORIZON = int(H * 0.80)

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


class CountdownApp:
    def __init__(self, root):
        self.root = root
        root.title("GTA VI — Launch Countdown")
        root.geometry(f"{W}x{H}")
        root.resizable(False, False)
        root.configure(bg=SKY_STOPS[0][1])
        self._set_icon()

        self.display_font = pick_font(
            root, "Impact", "Anton", "Bebas Neue", "Haettenschweiler",
            "Arial Black", "DejaVu Sans Condensed", "Helvetica")
        self.label_font = pick_font(
            root, "Futura", "Century Gothic", "Segoe UI", "Avenir Next",
            "DejaVu Sans", "Helvetica")

        self.c = tk.Canvas(root, width=W, height=H, highlightthickness=0, bd=0)
        self.c.pack(fill="both", expand=True)

        self.stars = []
        self._draw_scene()
        self._draw_title()
        self._build_countdown()
        root.bind("<Escape>", lambda e: root.destroy())
        self._tick()
        self._twinkle()

    # ---------- scene ----------
    def _set_icon(self):
        try:
            size = 32
            img = tk.PhotoImage(width=size, height=size)
            for y in range(size):
                col = gradient_at(SKY_STOPS, y / (size - 1))
                img.put(col, to=(0, y, size, y + 1))
            for y in range(8, 24):
                for x in range(size):
                    if (x - 16) ** 2 + (y - 22) ** 2 <= 100 and y % 4 != 3:
                        img.put(ORANGE if y < 16 else HOT_PINK, (x, y))
            self.root.iconphoto(True, img)
            self._icon = img
        except tk.TclError:
            pass

    def _draw_scene(self):
        c = self.c
        # Sky gradient
        for y in range(0, HORIZON, 2):
            c.create_rectangle(0, y, W, y + 2, width=0,
                               fill=gradient_at(SKY_STOPS, y / HORIZON))
        # Stars in the upper sky
        rnd = random.Random(1986)
        for _ in range(70):
            x, y = rnd.randint(0, W), rnd.randint(0, int(HORIZON * 0.38))
            r = rnd.choice((1, 1, 1, 1.5, 2))
            s = c.create_oval(x - r, y - r, x + r, y + r, width=0, fill="#ffffff")
            self.stars.append(s)

        # Retro striped sun sitting on the horizon
        cx, cy, R = W // 2, HORIZON + 10, 125
        for y in range(cy - R, HORIZON):
            dy = y - cy
            if abs(dy) > R:
                continue
            t = (y - (cy - R)) / (2 * R)
            # stripes widen toward the bottom
            if t > 0.22:
                band = int((t - 0.22) * 40)
                period = 12
                gap = 2 + band // 2
                if (y - (cy - R)) % period < gap:
                    continue
            half = math.sqrt(R * R - dy * dy)
            col = lerp_color("#fff27a", "#ff3d8b", min(1, t * 1.15))
            c.create_line(cx - half, y, cx + half, y, fill=col)

        # City skyline silhouette on the horizon
        rnd = random.Random(7)
        x = 0
        while x < W:
            bw = rnd.randint(14, 38)
            bh = rnd.randint(8, 34)
            if W * 0.30 < x < W * 0.70:
                bh = rnd.randint(18, 70)  # downtown towers
            c.create_rectangle(x, HORIZON - bh, x + bw, HORIZON,
                               fill="#2a0c3d", width=0)
            # lit windows
            for wy in range(HORIZON - bh + 5, HORIZON - 3, 7):
                for wx in range(x + 3, x + bw - 3, 6):
                    if rnd.random() < 0.18:
                        c.create_rectangle(wx, wy, wx + 2, wy + 2, width=0,
                                           fill=rnd.choice((ORANGE, HOT_PINK, CYAN)))
            x += bw + rnd.randint(0, 4)

        # Sea gradient
        for y in range(HORIZON, H, 2):
            t = (y - HORIZON) / (H - HORIZON)
            c.create_rectangle(0, y, W, y + 2, width=0, fill=gradient_at(SEA_STOPS, t))
        # Sun reflection shimmer
        rnd = random.Random(42)
        rows = (H - HORIZON - 8) // 6
        for i in range(rows):
            y = HORIZON + 4 + i * 6
            spread = 120 - i * 3 + rnd.randint(-15, 15)
            seg = rnd.randint(20, 80)
            off = rnd.randint(-spread, spread)
            fade = i / rows
            col = lerp_color("#ffd36b", "#5b1a6e", fade)
            c.create_line(cx + off - seg / 2, y, cx + off + seg / 2, y,
                          fill=col, width=2)
        # Horizon glow line
        c.create_line(0, HORIZON, W, HORIZON, fill="#ff8fb8", width=1)

        # Palm trees
        self._palm(70, H + 10, 300, lean=0.55)
        self._palm(165, H + 10, 220, lean=0.30, scale=0.75)
        self._palm(W - 60, H + 10, 330, lean=-0.50)
        self._palm(W - 170, H + 10, 240, lean=-0.25, scale=0.8)

    def _palm(self, bx, by, height, lean=0.4, scale=1.0):
        c = self.c
        # Trunk: quadratic curve with tapering width
        tx, ty = bx + lean * height * 0.6, by - height
        ctrl_x, ctrl_y = bx + lean * height * 0.05, by - height * 0.55
        left, right = [], []
        steps = 24
        for i in range(steps + 1):
            t = i / steps
            x = (1 - t) ** 2 * bx + 2 * (1 - t) * t * ctrl_x + t * t * tx
            y = (1 - t) ** 2 * by + 2 * (1 - t) * t * ctrl_y + t * t * ty
            w = (14 - 8 * t) * scale
            left.append((x - w / 2, y))
            right.append((x + w / 2, y))
        pts = left + right[::-1]
        c.create_polygon(*[v for p in pts for v in p], fill=SILHOUETTE, outline="")
        # trunk rings
        for i in range(2, steps, 2):
            (lx, ly), (rx, ry) = left[i], right[i]
            c.create_line(lx, ly, rx, ry, fill="#2b1140")

        # Fronds
        angles = [-170, -140, -110, -75, -40, -10, 20, 200, 160]
        for a in angles:
            self._frond(tx, ty, math.radians(a), 130 * scale)
        c.create_oval(tx - 9 * scale, ty - 7 * scale, tx + 9 * scale, ty + 7 * scale,
                      fill=SILHOUETTE, outline="")

    def _frond(self, x0, y0, ang, length):
        """A drooping leaf: spine curves downward under 'gravity'."""
        spine = []
        steps = 16
        for i in range(steps + 1):
            t = i / steps
            d = length * t
            droop = (t ** 2) * length * 0.55
            spine.append((x0 + math.cos(ang) * d, y0 + math.sin(ang) * d + droop))
        top, bot = [], []
        for i, (x, y) in enumerate(spine):
            t = i / steps
            w = math.sin(math.pi * t) * 13 * (1 - 0.3 * t)
            if i < steps:
                nx, ny = spine[i + 1]
            else:
                nx, ny = x + (x - spine[i - 1][0]), y + (y - spine[i - 1][1])
            dx, dy = nx - x, ny - y
            n = math.hypot(dx, dy) or 1
            px, py = -dy / n, dx / n
            top.append((x + px * w, y + py * w))
            bot.append((x - px * w * 0.6, y - py * w * 0.6))
        pts = top + bot[::-1]
        self.c.create_polygon(*[v for p in pts for v in p],
                              fill=SILHOUETTE, outline="", smooth=True)

    # ---------- text ----------
    def _glow_text(self, x, y, text, font, color, glow, layers=4, **kw):
        c = self.c
        for i in range(layers, 0, -1):
            col = lerp_color(glow, "#140a2e", i / (layers + 1))
            for dx, dy in ((-i, 0), (i, 0), (0, -i), (0, i)):
                c.create_text(x + dx, y + dy, text=text, font=font, fill=col, **kw)
        return c.create_text(x, y, text=text, font=font, fill=color, **kw)

    def _draw_title(self):
        c = self.c
        c.create_text(W // 2, 46, text="GRAND THEFT AUTO",
                      font=(self.display_font, 22), fill="#ffffff")
        # Big "VI": layered for a sunset-gradient feel
        big = (self.display_font, 96, "bold")
        self._glow_text(W // 2, 120, "VI", big, ORANGE, PINK, layers=5)
        c.create_text(W // 2, 120 + 3, text="VI", font=big, fill=HOT_PINK)
        c.create_text(W // 2, 120 - 3, text="VI", font=big, fill="#ffe08a")
        c.create_text(W // 2, 120, text="VI", font=big, fill=ORANGE)
        c.create_text(W // 2, 188,
                      text="WELCOME BACK TO VICE CITY  •  NOV 19, 2026",
                      font=(self.label_font, 12, "bold"), fill="#ffd6f0")

    # ---------- countdown ----------
    def _build_countdown(self):
        c = self.c
        self.units = []
        labels = ["DAYS", "HOURS", "MINUTES", "SECONDS"]
        box_w, box_h, gap = 150, 118, 22
        total = 4 * box_w + 3 * gap
        x0 = (W - total) // 2
        y0 = 214
        for i, lab in enumerate(labels):
            x = x0 + i * (box_w + gap)
            # neon frame: outer glow + inner panel
            for g, col in ((6, "#4a1450"), (4, "#8a1f78"), (2, PINK)):
                c.create_rectangle(x - g, y0 - g, x + box_w + g, y0 + box_h + g,
                                   outline=col, width=1)
            c.create_rectangle(x, y0, x + box_w, y0 + box_h, fill="#1b0b30",
                               outline=HOT_PINK, width=2)
            c.create_rectangle(x + 2, y0 + 2, x + box_w - 2, y0 + box_h * 0.45,
                               fill="#24103d", width=0)
            num_glow = c.create_text(x + box_w / 2 + 2, y0 + 52 + 2, text="00",
                                     font=(self.display_font, 56), fill="#7a1460")
            num = c.create_text(x + box_w / 2, y0 + 52, text="00",
                                font=(self.display_font, 56), fill="#ffffff")
            c.create_text(x + box_w / 2, y0 + box_h - 16, text=lab,
                          font=(self.label_font, 11, "bold"), fill=CYAN)
            self.units.append((num_glow, num))
            if i < 3:
                c.create_text(x + box_w + gap / 2, y0 + 50, text=":",
                              font=(self.display_font, 40), fill=HOT_PINK)

        self.status = c.create_text(W // 2, y0 + box_h + 26, text="",
                                    font=(self.label_font, 13, "bold"),
                                    fill="#ffffff")
        self.launched_ids = []

    def _tick(self):
        remaining = (LAUNCH - datetime.now()).total_seconds()
        if remaining <= 0:
            self._show_launched()
            return
        secs = int(remaining)
        d, rem = divmod(secs, 86400)
        h, rem = divmod(rem, 3600)
        m, s = divmod(rem, 60)
        for (glow, num), val in zip(self.units, (d, h, m, s)):
            txt = f"{val:02d}" if val < 100 else str(val)
            self.c.itemconfigure(glow, text=txt)
            self.c.itemconfigure(num, text=txt)
        if d == 0:
            msg = "LAUNCH DAY IS ALMOST HERE. CLEAR YOUR SCHEDULE."
        elif d == 1:
            msg = "ONE MORE DAY. CHARGE THE CONTROLLER."
        else:
            msg = f"{d} DAYS UNTIL LEONIDA"
        self.c.itemconfigure(self.status, text=msg)
        # schedule next tick right after the next whole second
        ms = int((remaining - secs) * 1000) + 15
        self.root.after(max(50, ms), self._tick)

    def _show_launched(self):
        for glow, num in self.units:
            self.c.itemconfigure(glow, text="00")
            self.c.itemconfigure(num, text="00")
        self.c.itemconfigure(self.status, text="")
        self._glow_text(W // 2, 214 + 118 + 28, "IT'S OUT. GO PLAY.",
                        (self.display_font, 34), "#ffffff", PINK, layers=4)

    def _twinkle(self):
        for s in random.sample(self.stars, 8):
            self.c.itemconfigure(s, fill=random.choice(
                ("#ffffff", "#ffd6f0", "#b9a4ff", "#5a3a8a")))
        self.root.after(400, self._twinkle)


def main():
    root = tk.Tk()
    CountdownApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
