import subprocess
import threading
from pathlib import Path

CHIME_PATH = Path(__file__).parent.parent / "assets" / "sounds" / "chime.wav"
SYSTEM_SOUND = "/System/Library/Sounds/Tink.aiff"


def play_chime():
    """Play a gentle chime sound in background thread."""
    sound_path = str(CHIME_PATH) if CHIME_PATH.exists() else SYSTEM_SOUND

    def _play():
        subprocess.run(["afplay", sound_path], check=False)

    threading.Thread(target=_play, daemon=True).start()
