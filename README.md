# ZenBreak

**Your AI-powered desk health guardian for macOS.**

ZenBreak watches how you work — which apps you use, how intensely you type — and delivers the right break at the right time. Not a dumb timer. A personal PT that knows when your wrists need a stretch vs. when your eyes need rest.

---

## Why ZenBreak?

Every break reminder app fails for the same reasons:

1. **You mindlessly click "skip"** — ZenBreak has no skip button. The overlay stays until you do the exercise.
2. **Same "take a break" every 30 min** — ZenBreak tracks 6 body areas and prescribes the exercise you actually need.
3. **Interrupts during meetings** — ZenBreak detects Zoom/Teams/WeChat and suppresses until you're done.
4. **Goes stale after a week** — AI generates fresh, context-aware messages. Gamification keeps you engaged.

## What Makes It Different

| Feature | Other Apps | ZenBreak |
|---------|-----------|----------|
| **Reminder trigger** | Fixed timer (every 30 min) | Activity-aware strain model (6 body areas) |
| **What it knows** | Nothing — just time | Which app, typing intensity, session duration |
| **Break content** | "Take a break" | Specific exercise with YouTube video demo |
| **Skip behavior** | Easy skip button | No skip — exercise countdown, then dismiss |
| **Meeting awareness** | None | Detects Zoom/Teams/WeChat/WeCom, auto-suppresses |
| **AI** | None | Personalized messages via local Ollama LLM |
| **Late night** | Same as daytime | More aggressive after 10pm |
| **Gamification** | None | XP, health ranks, streaks, daily challenges |

## Screenshots

*Coming soon*

## Quick Start

### Prerequisites

- macOS 12+
- Python 3.10+
- [Ollama](https://ollama.com) (optional, for AI messages)

### Install

```bash
git clone https://github.com/swiftwind16/zenbreak.git
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

Six body areas accumulate strain independently based on what you're doing. When any area crosses the threshold (50%, or 30% in late night mode), a break fires for that specific body area.

Strain includes natural decay — it slowly decreases over time so areas don't permanently max out. After each break, the affected area recovers significantly. A 30-minute cooldown ensures breaks are spaced apart.

### 3. Escalating Enforcement

```
Level 1 (0s):     Gentle chime + menu bar shows "eyes now"
Level 2 (+30s):   macOS notification with exercise name
Level 3 (+60s):   Full-screen overlay with exercise + video demo
```

The overlay shows:
- Exercise name and step-by-step instructions
- "Watch demo" button to load YouTube video inline
- AI-generated context message (why this break, why now)
- Countdown timer ("Do this for 20s")
- "I did it" button (always visible)
- Escape key as emergency exit

### 4. Smart Behavior

- **Idle detection** — No input for 5+ min → timers pause, strain recovers
- **Meeting detection** — Zoom/Teams/WeChat/WeCom/FaceTime frontmost → suppressed with 1-min grace after
- **Late night mode** — After 10pm, threshold drops to 30% for more frequent breaks
- **Strain persistence** — Strain data survives app restarts (within 10 min)
- **30-min cooldown** — Minimum gap between breaks to protect deep work flow

### 5. AI-Powered Messages

Local Ollama (qwen2.5:7b) generates context-aware messages based on your current activity:

> "45 minutes of heavy keyboard work in Cursor — your forearm extensors are overloaded. Wrist extensions now."

> "Long evening session in Terminal — your neck has been locked forward. Chin tucks and lateral stretches."

Messages are pre-generated on startup and cached. Works offline with no message (just exercise steps).

### 6. Gamification

**XP System:**
| Action | XP |
|--------|-----|
| Complete a break | +10 |
| Complete with video demo | +15 |
| First break of the day | +20 bonus |
| Complete daily challenge | +50 |

**Health Ranks:**
Beginner → Aware → Active → Consistent → Dedicated → Athlete → Guardian → Zen Master

**Streaks:** Maintain 3+ breaks per day. One-day freeze forgiveness if you miss.

**Daily Challenges** (rotating):
- Complete 5 breaks today
- Hit all 6 body areas
- Take 3 wrist breaks
- Complete a break before 10am
- Watch 2 demo videos

## Exercise Library

16 exercises across 6 body areas, each with step-by-step instructions and a YouTube demo video:

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
Z  neck 12m                     ← icon + countdown with body area
────────────────────────────────
Next: Chin Tucks in 12m         ← what's coming and when
3 breaks today · 2d streak      ← stats + streak
Level 3: Active · 550 XP        ← gamification rank
Complete 5 breaks today (2/5)   ← daily challenge

Take a break now              ▶  (submenu: Auto + all body areas)
Pause                         ▶  (15m / 30m / 1hr / Resume)

Quit ZenBreak
```

After completing a break, the title bar briefly shows `+10 XP` for 3 seconds.

## Configuration

Config file: `~/.zenbreak/config.json`

```json
{
  "work_hours": { "start": "09:00", "end": "01:00" },
  "idle_threshold_sec": 300,
  "return_grace_min": 1,
  "escalation": {
    "level_2_delay_sec": 30,
    "level_3_delay_sec": 60,
    "level_4_delay_sec": 90,
    "dismiss_countdown_sec": 10
  }
}
```

## Data Storage

All data is local — nothing leaves your machine.

```
~/.zenbreak/
├── config.json          # User settings
├── game.json            # XP, rank, streaks, challenges
├── strain.json          # Current strain levels (persists across restarts)
├── stats/
│   └── 2026-03-20.json  # Daily break stats
└── videos/              # Cached exercise demo videos (optional)
```

## Tech Stack

- **Python 3.12** — core language
- **rumps** — macOS menu bar framework
- **pyobjc** — native macOS APIs (NSWindow, AppKit, Quartz, WebKit)
- **Ollama** — local AI message generation (qwen2.5:7b)
- ~2,600 lines of code, 32 tests

## Architecture

```
zenbreak/
├── app.py              # Main loop: activity → strain → reminders → overlay
├── activity.py         # Frontmost app + keyboard/mouse intensity tracking
├── strain.py           # Body strain model (6 areas, natural decay, persistence)
├── timers.py           # Escalation engine with 30-min cooldown
├── exercises.py        # 16 exercises with YouTube video URLs
├── overlay.py          # Full-screen native overlay (NSWindow + WKWebView)
├── ai.py               # Ollama integration + message caching
├── video.py            # Local HTTP server for YouTube embed playback
├── gamification.py     # XP, health ranks, streaks, daily challenges
├── stats.py            # Daily stats + streak persistence
├── sound.py            # Gentle chime
├── idle.py             # Idle detection (Quartz)
└── config.py           # Config loading with deep merge
```

## Roadmap

- [ ] Adaptive scheduling (learns when you comply vs. dismiss)
- [ ] Natural language config ("be gentle before noon")
- [ ] Weekly health summary report
- [ ] Social features (team streaks, leaderboards)
- [ ] Swift rewrite for Mac App Store
- [ ] Freemium model (free tier + Pro)

## Contributing

PRs welcome! See `docs/plans/` for design docs and implementation details.

## License

MIT
