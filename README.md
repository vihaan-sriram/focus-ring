# Focus Ring

A 20-20-20 eye-break timer designed around a camera lens's focus scale — the ring literally sweeps to a **20 FT** mark on a distance scale, because that's what the rule asks you to look at.

> Every 20 minutes, look at something 20 feet away for 20 seconds.

Two implementations, same design language:

| | Web | Windows |
|---|---|---|
| **Where it lives** | A browser tab | System tray |
| **How it interrupts you** | Tab title + notification | Fullscreen overlay over every window |
| **Setup** | Open the HTML file | `pip install` + run |
| **Best for** | Quick use, any OS | Actually can't be ignored |

## Web version

`web/focus-ring.html` — a single self-contained file. Open it in any browser and pin the tab.

- Countdown ring styled as a lens distance scale (1ft → ∞)
- Tab title tracks the timer live, so you don't need to switch to it
- Desktop notification + chime at each transition
- Breaks-today and streak persist locally

No install, no dependencies, works on any OS with a browser.

## Windows version

`windows/focus_ring.py` — a native tray app. When the 20 minutes are up, a translucent fullscreen overlay appears **over every other window** — no ignoring it from inside your editor.

```bash
cd windows
pip install -r requirements.txt
pythonw focus_ring.py       # runs silently, tray icon only
```

Right-click the tray icon for manual break, pause/resume, and streak stats. Add a shortcut in `shell:startup` (targeting `pythonw.exe path\to\focus_ring.py`) to run it on login.

Stats persist at `~/.focus_ring/stats.json`.

## Why this design

Eye-strain tools tend to look like generic productivity timers. This one is built around the actual physical object the rule references — a lens barrel's distance scale — so the UI teaches you what it's asking for just by looking at it: the ring isn't just counting down, it's sweeping toward 20 feet.

## License

MIT — see [LICENSE](LICENSE).
