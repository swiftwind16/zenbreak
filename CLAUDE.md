# CLAUDE.md — ZenBreak

## Project Overview
ZenBreak is a macOS menu bar app that acts as your personal desk health guardian — it monitors your work activity (frontmost app + keyboard/mouse intensity), tracks cumulative body strain, and delivers escalating, activity-aware health reminders with specific exercise prescriptions.

## Tech Stack
- **Python 3.12** — core language
- **rumps** — macOS menu bar framework (wraps pyobjc)
- **pyobjc / AppKit** — native macOS APIs (frontmost app detection, NSWindow overlays)
- **Quartz / CoreGraphics** — idle detection, input event monitoring
- **Pillow** — image handling (for v2 GIF support)
- **Claude API (anthropic)** — AI-generated messages (v2)

## Project Structure
```
zenbreak/
├── zenbreak/           # Main package
│   ├── app.py          # Menu bar app entry point (rumps)
│   ├── activity.py     # App tracking + input intensity monitoring
│   ├── strain.py       # Body strain model (accumulation + recovery)
│   ├── timers.py       # Reminder scheduling + 4-level escalation
│   ├── exercises.py    # Exercise library per body area
│   ├── overlay.py      # Full-screen native overlay window
│   ├── sound.py        # Chime playback
│   ├── idle.py         # Idle detection via Quartz
│   └── config.py       # Config loading with deep merge
├── assets/             # Sounds, illustrations
├── tests/              # Unit + integration tests
├── config.default.json # Default configuration
└── docs/plans/         # Implementation plans
```

## Running
```bash
# Run the app
python3 -m zenbreak.app

# Run tests
python3 -m pytest tests/ -v

# Install as login item
bash install.sh
```

## Key Architectural Decisions
- **Activity-aware strain model**: Instead of fixed timers, strain accumulates per body area based on what app you're using and how intensely you're typing/mousing. The highest-strain body area gets the next reminder.
- **Escalating enforcement**: 4 levels (chime → notification → semi-transparent overlay → full overlay with countdown). No skip button — only "I did it" after countdown.
- **Idle detection resets strain**: If you step away for >2 min, timers pause and strain partially recovers. 5-min grace period on return.
- **All state is local**: Config in `~/.zenbreak/config.json`, stats in `~/.zenbreak/stats/`.

## Development Rules
- **TDD**: Write failing test first, then implement, then refactor
- **One commit per logical change**: Small, focused commits
- **No Electron**: We use native macOS APIs via pyobjc for lightweight performance
- **Use subprocess.run() for shell commands**: Never use unsafe shell execution methods
- **No secrets in code**: API keys go in `.env` or `~/.zenbreak/config.json` (gitignored)

## Testing
- Unit tests in `tests/test_*.py`
- Integration test in `tests/test_integration.py`
- Overlay/UI: manual smoke test only (native UI can't be unit tested easily)
- Run: `python3 -m pytest tests/ -v`

## Claude Code Settings (settings.json)
```json
{
  "permissions": {
    "defaultMode": "acceptEdits",
    "allow": [
      "Bash(npm run *)",
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(ls *)",
      "Bash(grep *)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(git push *)"
    ]
  }
}
```

## Git Workflow
- Work on feature branches: `feature/`, `fix/`, `refactor/`
- Never push directly to main
- Commit message prefixes: `feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`
