# AI App Classification + Health Focus Design

**Goal:** Auto-classify unknown apps via AI, and let users prioritize body areas they care about most.

## 1. Smart App Classification

When an app is not in the hardcoded `APP_CATEGORIES` map:
- Ask Ollama: "What kind of app is [app name]? Reply with one word: ide, terminal, browser, video_call, messaging, design, reading, or other"
- Cache the result in `~/.zenbreak/app_cache.json`
- Only ask once per app — subsequent lookups use the cache
- If Ollama is unavailable, fall back to "other"

## 2. Health Focus Menu

Menu item: "My health focus" submenu with toggleable body areas.
- Checked areas get 1.5x strain multiplier — breaks target them more often
- Unchecked areas accumulate normally (1.0x)
- Persisted in `~/.zenbreak/config.json` under `"health_focus": ["wrists", "eyes"]`
- Default: nothing checked (all areas equal)

## Where it fits

- `activity.py`: add AI classification fallback for unknown bundle IDs
- `strain.py`: apply health focus multiplier in `update()`
- `app.py`: add "My health focus" submenu with toggle callbacks
- `~/.zenbreak/app_cache.json`: cached AI classifications
- `~/.zenbreak/config.json`: health focus preferences
