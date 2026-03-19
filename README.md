# ZenBreak

**Your AI-powered desk health guardian for macOS.**

ZenBreak watches how you work — which apps you use, how intensely you type — and delivers the right break at the right time. Not a dumb timer. A personal PT that knows when your wrists need a stretch vs. when your eyes need rest.

https://github.com/yourusername/zenbreak

---

## Why ZenBreak?

Every break reminder app fails for the same reasons:

1. **You mindlessly click "skip"** — ZenBreak has no skip button. The overlay stays until you do the exercise.
2. **Same "take a break" every 30 min** — ZenBreak tracks 6 body areas and prescribes the exercise you actually need.
3. **Interrupts during meetings** — ZenBreak detects Zoom/Teams/WeChat and suppresses until you're done.
4. **Goes stale after a week** — AI generates fresh, context-aware messages every time.

## What Makes It Different

| Feature | Other Apps | ZenBreak |
|---------|-----------|----------|
| **Reminder trigger** | Fixed timer (every 30 min) | Activity-aware strain model (6 body areas) |
| **What it knows** | Nothing — just time | Which app, typing intensity, session duration |
| **Break content** | "Take a break" | Specific exercise with video demo |
| **Skip behavior** | Easy skip button | No skip — exercise countdown, then dismiss |
| **Meeting awareness** | None | Detects Zoom/Teams/WeChat, auto-suppresses |
| **AI** | None | Personalized messages via local LLM |
| **Late night** | Same as daytime | More aggressive after 10pm |

## Screenshots

*Coming soon*

## Quick Start

### Prerequisites

- macOS 12+
- Python 3.10+
- [Ollama](https://ollama.com) (optional, for AI messages)

### Install

```bash
git clone https://github.com/yourusername/zenbreak.git
cd zenbreak
pip install -r requirements.txt

# Optional: pull the AI model
ollama pull qwen2.5:7b

# Run it
python3 -m zenbreak.app
```

### Auto-start at Login

```bash
bash install.sh
```

### Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.zenbreak.app.plist
rm ~/Library/LaunchAgents/com.zenbreak.app.plist
```

## How It Works

### 1. Activity Monitoring

ZenBreak polls every 5 seconds:
- **Which app** is in the foreground (Terminal, Cursor, Chrome, Zoom...)
- **Keyboard intensity** (idle / light / medium / heavy typing)
- **Mouse intensity** (clicking, scrolling)

Different activities stress different body parts:

| Activity | Primary Strain |
|----------|---------------|
| Terminal / IDE (heavy typing) | Wrists, eyes, neck |
| Browser (scrolling/reading) | Eyes, back |
| Video calls (fixed position) | Neck, shoulders, eyes |
| Messaging | Low strain overall |

### 2. Body Strain Model

Six body areas accumulate strain independently:

```
Eyes         ████████░░  80%  ← 2hr of Cursor, only 1 eye break
Wrists       ███████░░░  70%  ← heavy keyboard all morning
Neck         ██████░░░░  60%  ← leaning into terminal
Shoulders    ████░░░░░░  40%
Back         ███░░░░░░░  30%
Circulation  ██░░░░░░░░  20%
```

When any area crosses 50% (or 30% in late night mode), a reminder fires for that specific body area.

### 3. Escalating Enforcement

```
Level 1 (0s):     Menu bar icon flashes + gentle chime
Level 2 (+30s):   macOS notification
Level 3 (+60s):   Semi-transparent overlay
Level 4 (+90s):   Full-screen overlay with exercise + video demo
```

No skip button. The overlay shows:
- Exercise name and steps
- YouTube demo video (streamed inline)
- Countdown timer ("Do this for 20s")
- "I did it" button (always visible)
- Escape key as emergency exit

### 4. Smart Behavior

- **Idle detection** — Step away for 2+ min → timers pause, strain recovers
- **Meeting detection** — Zoom/Teams/WeChat/WeCom frontmost → suppressed
- **Late night mode** — After 10pm, threshold drops to 30% (breaks every ~18 min)
- **Return grace** — After idle/meeting, 1-5 min grace before reminders resume

### 5. AI-Powered Messages

Local Ollama generates context-aware messages:

> "45 minutes of heavy keyboard work in Cursor — your forearm extensors are overloaded. Wrist extensions now."

> "Long evening session in Terminal — your neck has been locked forward. Chin tucks and lateral stretches."

Messages are pre-generated and cached. Works offline with static fallback messages.

## Exercise Library

16 exercises across 6 body areas, each with:
- Step-by-step instructions
- YouTube demo video (streamed in overlay)
- Recommended duration

| Area | Exercises |
|------|-----------|
| **Eyes** | 20-20-20 Rule, Eye Rolling, Palming |
| **Neck** | Neck Rolls, Chin Tucks, Lateral Stretch |
| **Wrists** | Wrist Extensions, Prayer Stretch, Finger Spreads |
| **Shoulders** | Shoulder Shrugs, Arm Across Chest |
| **Back** | Seated Spinal Twist, Standing Back Extension |
| **Circulation** | Stand and Walk, Calf Raises |

## Menu Bar

```
🧘 12m                          ← countdown to next break
────────────────────────────────
Current: Cursor (ide)
Strain: eyes 23% | neck 18% | wrists 12%
Next break: eyes at 50% (now 23%)

Breaks: 5 | Most: eyes | Streak: 3d

Take a break now              ▶  (submenu with all body areas)

Pause 15 min
Pause 30 min
Pause 1 hour
Resume
Quit
```

## Configuration

Config file: `~/.zenbreak/config.json`

```json
{
  "work_hours": { "start": "10:00", "end": "01:00" },
  "idle_threshold_sec": 120,
  "return_grace_min": 5,
  "escalation": {
    "level_2_delay_sec": 30,
    "level_3_delay_sec": 60,
    "level_4_delay_sec": 90,
    "dismiss_countdown_sec": 10
  }
}
```

## Stats & Streaks

Daily stats persist to `~/.zenbreak/stats/`:
- Breaks taken vs. offered
- Breaks by body area
- Compliance percentage
- Consecutive day streaks (80%+ compliance)

## Tech Stack

- **Python 3.12** — core
- **rumps** — macOS menu bar
- **pyobjc** — native macOS APIs (NSWindow, AppKit, Quartz, WebKit, AVKit)
- **Ollama** — local AI (qwen2.5:7b)
- ~2,300 lines of code, 35 tests

## Architecture

```
zenbreak/
├── app.py          # Main loop: activity → strain → reminders → overlay
├── activity.py     # Frontmost app + keyboard/mouse intensity tracking
├── strain.py       # Body strain model (6 areas, activity-specific rates)
├── timers.py       # 4-level escalation engine
├── exercises.py    # 16 exercises with video URLs
├── overlay.py      # Full-screen native overlay (NSWindow + WKWebView)
├── ai.py           # Ollama integration + message caching
├── video.py        # Local HTTP server for YouTube embed
├── stats.py        # Daily stats + streak persistence
├── sound.py        # Gentle chime
├── idle.py         # Idle detection (Quartz)
└── config.py       # Config loading
```

## Roadmap

- [ ] Adaptive scheduling (learns when you comply vs. dismiss)
- [ ] Natural language config ("be gentle before noon")
- [ ] Weekly health summary report
- [ ] Cumulative strain tracking across days
- [ ] Swift rewrite for Mac App Store
- [ ] Team/enterprise features

## Contributing

PRs welcome! See `docs/plans/` for implementation details.

## License

MIT
