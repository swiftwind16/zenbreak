"""App classification — heuristic first, AI fallback, cached results."""

import json
import logging
import re
import urllib.request
import urllib.error
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_PATH = Path.home() / ".zenbreak" / "app_cache.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b"

VALID_CATEGORIES = {"ide", "terminal", "browser", "video_call", "messaging", "design", "reading", "other"}

# Heuristic rules: (pattern, category)
# Matched against app name (case-insensitive) and bundle ID
_NAME_RULES = [
    # Terminals
    (r"terminal|iterm|warp|hyper|kitty|alacritty|konsole|putty|securecrt|shell", "terminal"),

    # IDEs and code editors
    (r"cursor|vs\s?code|visual\s?studio|pycharm|intellij|webstorm|phpstorm|rider|goland|"
     r"rubymine|clion|datagrip|android\s?studio|xcode|sublime|atom|brackets|nova|"
     r"textmate|bbedit|coda|vim|nvim|neovim|emacs|eclipse|netbeans|code\s?runner|"
     r"codeedit|zed|fleet", "ide"),

    # Browsers
    (r"chrome|firefox|safari|brave|edge|opera|vivaldi|arc|orion|tor\s?browser|"
     r"chromium|duckduckgo|waterfox|librewolf|floorp|zen\s?browser", "browser"),

    # Video calls
    (r"zoom|teams|meet|facetime|skype|webex|gotomeeting|ringcentral|"
     r"bluejeans|whereby|around|loom|screen\.so|"
     r"google\s?duo|houseparty|jitsi", "video_call"),

    # Messaging
    (r"slack|discord|telegram|whatsapp|wechat|wecom|messenger|signal|"
     r"imessage|messages|line|viber|kakaotalk|wire|element|matrix|"
     r"rocket\.?chat|mattermost|zulip|qq|dingtalk|feishu|lark", "messaging"),

    # Design tools
    (r"figma|sketch|adobe\s?xd|invision|zeplin|framer|principle|origami|"
     r"photoshop|illustrator|indesign|affinity|canva|pixelmator|gimp|"
     r"blender|maya|cinema\s?4d|after\s?effects|premiere|davinci|"
     r"final\s?cut|motion|procreate|lightroom|capture\s?one", "design"),

    # Reading / writing / docs
    (r"pdf|preview|kindle|ibooks|books|calibre|readdle|goodreader|"
     r"notion|obsidian|roam|logseq|bear|ulysses|ia\s?writer|scrivener|"
     r"typora|marktext|joplin|evernote|onenote|apple\s?notes|"
     r"google\s?docs|word(?!press)|pages|libreoffice|openoffice|"
     r"overleaf|latex|texshop|quip|dropbox\s?paper|coda(?!.*code)|"
     r"reader|acrobat", "reading"),

    # Spreadsheets / data (similar to reading — low keyboard, high eye)
    (r"excel|sheets|numbers|airtable|tableplus|sequel\s?pro|"
     r"mysql\s?workbench|pgadmin|datagrip|dbeaver|mongodb\s?compass|"
     r"postico|beekeeper", "reading"),

    # Email (similar to messaging)
    (r"mail|outlook|thunderbird|spark|airmail|canary|mimestream|"
     r"hey\.com|proton\s?mail|fastmail|superhuman|mailspring|postbox", "messaging"),

    # Music / media (low strain — passive listening)
    (r"spotify|music|itunes|podcasts|audible|youtube\s?music|"
     r"soundcloud|tidal|deezer|pandora|vlc|iina|mpv|quicktime|"
     r"plex|infuse", "other"),

    # System utilities (low strain)
    (r"finder|system\s?preferences|settings|activity\s?monitor|"
     r"disk\s?utility|console|keychain|migration|time\s?machine|"
     r"app\s?store|software\s?update|installer", "other"),
]

_BUNDLE_RULES = [
    # Apple apps by bundle prefix
    (r"com\.apple\.dt\.", "ide"),         # Xcode and dev tools
    (r"com\.apple\.mail", "messaging"),
    (r"com\.apple\.MobileSMS", "messaging"),
    (r"com\.apple\.Safari", "browser"),
    (r"com\.apple\.Terminal", "terminal"),
    (r"com\.apple\.FaceTime", "video_call"),
    (r"com\.apple\.iWork\.", "reading"),
    (r"com\.apple\.Notes", "reading"),
    (r"com\.apple\.Preview", "reading"),
    (r"com\.apple\.Books", "reading"),

    # JetBrains family
    (r"com\.jetbrains\.", "ide"),

    # Adobe family
    (r"com\.adobe\.(photoshop|illustrator|indesign|xd|aftereffects|premiere|lightroom)", "design"),
    (r"com\.adobe\.acrobat|com\.adobe\.Reader", "reading"),

    # Microsoft
    (r"com\.microsoft\.VSCode", "ide"),
    (r"com\.microsoft\.teams", "video_call"),
    (r"com\.microsoft\.Outlook|com\.microsoft\.onenote", "messaging"),
    (r"com\.microsoft\.Word|com\.microsoft\.Excel|com\.microsoft\.Powerpoint", "reading"),

    # Google
    (r"com\.google\.Chrome", "browser"),
    (r"com\.google\.meet", "video_call"),

    # Electron apps (common pattern)
    (r"com\.electron\.", "other"),
    (r"com\.todesktop\.", "ide"),  # Cursor and similar
]


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_cache(cache: dict):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def classify_app(app_name: str, bundle_id: str) -> str:
    """Classify an app. Cache → heuristic → AI → fallback."""
    # 1. Check cache
    cache = _load_cache()
    if bundle_id in cache:
        return cache[bundle_id]

    # 2. Heuristic: check bundle ID patterns
    for pattern, category in _BUNDLE_RULES:
        if re.search(pattern, bundle_id, re.IGNORECASE):
            _cache_result(cache, bundle_id, category, "bundle_rule")
            return category

    # 3. Heuristic: check app name patterns
    for pattern, category in _NAME_RULES:
        if re.search(pattern, app_name, re.IGNORECASE):
            _cache_result(cache, bundle_id, category, "name_rule")
            return category

    # 4. AI fallback (if Ollama available)
    ai_result = _ask_ollama(app_name)
    if ai_result:
        _cache_result(cache, bundle_id, ai_result, "ai")
        return ai_result

    # 5. Default
    _cache_result(cache, bundle_id, "other", "default")
    return "other"


def _cache_result(cache: dict, bundle_id: str, category: str, source: str):
    cache[bundle_id] = category
    _save_cache(cache)
    logger.info("[classifier] %s → %s (via %s)", bundle_id, category, source)


def _ask_ollama(app_name: str) -> str | None:
    """Ask Ollama to classify an app. Returns category or None."""
    prompt = (
        f"What kind of app is '{app_name}'? "
        f"Reply with exactly one word from this list: "
        f"ide, terminal, browser, video_call, messaging, design, reading, other. "
        f"Nothing else, just the one word."
    )

    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 10},
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            answer = data.get("response", "").strip().lower().rstrip(".")
            if answer in VALID_CATEGORIES:
                return answer
            logger.warning("[classifier] Unexpected AI answer for %s: %s", app_name, answer)
    except urllib.error.URLError:
        logger.debug("[classifier] Ollama not available")
    except Exception as e:
        logger.warning("[classifier] AI classification failed for %s: %s", app_name, e)

    return None
