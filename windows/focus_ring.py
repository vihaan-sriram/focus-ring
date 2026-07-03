"""
Focus Ring — a 20-20-20 eye-break tool that overlays your entire screen.

Every 20 minutes, a translucent fullscreen overlay appears on top of every
window on your desktop and asks you to look at something 20 feet away for
20 seconds. It auto-dismisses. Lives in the system tray the rest of the time.

SETUP (Windows):
    pip install pystray pillow

RUN (no console window):
    pythonw focus_ring.py
    (use "python focus_ring.py" instead if you want to see console output/errors)

RUN AT STARTUP:
    Win+R -> shell:startup -> create a shortcut there targeting:
        pythonw.exe "C:\\full\\path\\to\\focus_ring.py"
"""

import json
import math
import os
import threading
import time
import tkinter as tk
from datetime import date, timedelta

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

# ---------------------------------------------------------------- config --
WORK_SECONDS = 20 * 60
BREAK_SECONDS = 20

SAGE = "#5C7A63"
AMBER = "#C98A4B"
INK = "#EEF2ED"
INK_SOFT = "#B9C3BB"
BG_SCRIM = "#111814"

STATS_DIR = os.path.join(os.path.expanduser("~"), ".focus_ring")
STATS_FILE = os.path.join(STATS_DIR, "stats.json")


# ---------------------------------------------------------------- stats ---
def _load_stats():
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_stats(data):
    os.makedirs(STATS_DIR, exist_ok=True)
    with open(STATS_FILE, "w") as f:
        json.dump(data, f)


def record_break():
    data = _load_stats()
    today = date.today().isoformat()
    data[today] = data.get(today, 0) + 1
    _save_stats(data)
    return breaks_today(), current_streak()


def breaks_today():
    data = _load_stats()
    return data.get(date.today().isoformat(), 0)


def current_streak():
    data = _load_stats()
    streak = 0
    d = date.today()
    while data.get(d.isoformat(), 0) > 0:
        streak += 1
        d = d - timedelta(days=1)
    return streak


# ---------------------------------------------------------------- chime ---
def chime(pattern="break"):
    if not HAS_WINSOUND:
        return
    def _play():
        try:
            if pattern == "break":
                winsound.Beep(660, 160)
                winsound.Beep(880, 220)
            else:
                winsound.Beep(880, 120)
                winsound.Beep(660, 160)
        except RuntimeError:
            pass
    threading.Thread(target=_play, daemon=True).start()


# ---------------------------------------------------------------- overlay -
class Overlay:
    """Fullscreen, always-on-top, click-through-free scrim with a focus ring."""

    def __init__(self, root, on_close=None):
        self.root = root
        self.on_close = on_close
        self.remaining = BREAK_SECONDS
        self.total = BREAK_SECONDS
        self.win = tk.Toplevel(root)
        self.win.attributes("-fullscreen", True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.94)
        self.win.overrideredirect(True)
        self.win.configure(bg=BG_SCRIM)
        self.win.bind("<Escape>", lambda e: self._close())
        self.win.bind("<Button-1>", lambda e: self._close())
        self.win.focus_force()

        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()

        self.canvas = tk.Canvas(self.win, width=sw, height=sh,
                                 bg=BG_SCRIM, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        cx, cy, r = sw / 2, sh / 2 - 20, 130

        self.canvas.create_oval(cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6,
                                 outline="#2A342D", width=2)
        self.arc = self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=0, style="arc", outline=AMBER, width=6
        )
        self.time_text = self.canvas.create_text(
            cx, cy, text=str(BREAK_SECONDS), font=("Segoe UI Semibold", 64),
            fill=INK
        )
        self.canvas.create_text(
            cx, cy + 190, text="LOOK 20 FEET AWAY",
            font=("Segoe UI", 15, "bold"), fill=AMBER
        )
        self.canvas.create_text(
            cx, cy + 220,
            text="Find the far wall, a window, anything distant — rest your eyes on it.",
            font=("Segoe UI", 11), fill=INK_SOFT
        )
        self.canvas.create_text(
            cx, sh - 40, text="click anywhere or press Esc to skip",
            font=("Consolas", 9), fill="#5A655E"
        )

        chime("break")
        self._tick()

    def _tick(self):
        if self.remaining <= 0:
            self._close()
            return
        frac = (self.total - self.remaining) / self.total
        self.canvas.itemconfig(self.arc, extent=-360 * frac)
        self.canvas.itemconfig(self.time_text, text=str(self.remaining))
        self.remaining -= 1
        self.win.after(1000, self._tick)

    def _close(self):
        try:
            self.win.destroy()
        except Exception:
            pass
        if self.on_close:
            self.on_close()


# ---------------------------------------------------------------- app -----
class FocusRingApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # no main window, tray-only

        self.phase = "work"
        self.remaining = WORK_SECONDS
        self.paused = False
        self.overlay = None
        self.tray_icon = None

        self.root.after(1000, self._tick)

        if HAS_TRAY:
            threading.Thread(target=self._start_tray, daemon=True).start()

    # ---- timer loop (runs on Tk main thread) ----
    def _tick(self):
        if not self.paused and self.overlay is None:
            self.remaining -= 1
            if self.remaining <= 0:
                if self.phase == "work":
                    self._start_break()
                else:
                    self._start_work()
        self._update_tray_title()
        self.root.after(1000, self._tick)

    def _start_break(self):
        self.phase = "break"
        self.overlay = Overlay(self.root, on_close=self._end_break)

    def _end_break(self):
        self.overlay = None
        today_count, streak = record_break()
        chime("resume")
        self._start_work()
        self._notify_tray(f"Back to focus — {today_count} breaks today, {streak} day streak.")

    def _start_work(self):
        self.phase = "work"
        self.remaining = WORK_SECONDS

    def take_break_now(self):
        def _go():
            if self.overlay is None:
                self._start_break()
        self.root.after(0, _go)

    def toggle_pause(self):
        self.paused = not self.paused

    def quit(self):
        def _go():
            if self.tray_icon:
                self.tray_icon.stop()
            self.root.quit()
            os._exit(0)
        self.root.after(0, _go)

    # ---- tray ----
    def _tray_image(self):
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        color = AMBER if self.phase == "break" else SAGE
        d.ellipse([6, 6, size - 6, size - 6], outline=color, width=6)
        d.ellipse([size / 2 - 5, size / 2 - 5, size / 2 + 5, size / 2 + 5], fill=color)
        return img

    def _update_tray_title(self):
        if self.tray_icon:
            mins, secs = divmod(max(self.remaining, 0), 60)
            state = "break" if self.phase == "break" else "focus"
            self.tray_icon.title = f"Focus Ring — {mins:02d}:{secs:02d} ({state})"

    def _notify_tray(self, msg):
        if self.tray_icon:
            try:
                self.tray_icon.notify(msg, "Focus Ring")
            except Exception:
                pass

    def _start_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("Take a break now", lambda: self.take_break_now()),
            pystray.MenuItem("Pause / Resume", lambda: self.toggle_pause()),
            pystray.MenuItem(
                lambda item: f"Breaks today: {breaks_today()}", lambda: None, enabled=False
            ),
            pystray.MenuItem(
                lambda item: f"Streak: {current_streak()} days", lambda: None, enabled=False
            ),
            pystray.MenuItem("Quit", lambda: self.quit()),
        )
        self.tray_icon = pystray.Icon("focus_ring", self._tray_image(), "Focus Ring", menu)
        self.tray_icon.run()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if not HAS_TRAY:
        print("Tray icon disabled — run: pip install pystray pillow")
    app = FocusRingApp()
    app.run()
