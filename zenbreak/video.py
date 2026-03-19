"""Local HTTP server for YouTube embed playback."""

import http.server
import logging
import re
import threading

logger = logging.getLogger(__name__)

_server = None
_port = 0


def _extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from URL."""
    patterns = [
        r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


class _EmbedHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        video_id = self.path.strip('/')
        html = f'''<!DOCTYPE html>
<html><head><style>
html, body {{ margin:0; padding:0; width:100%; height:100%; background:#000; overflow:hidden; }}
iframe {{ position:absolute; top:0; left:0; width:100%; height:100%; border:none; }}
</style></head><body>
<iframe src="https://www.youtube.com/embed/{video_id}?autoplay=1&rel=0&modestbranding=1&playsinline=1"
    allow="autoplay; encrypted-media" allowfullscreen></iframe>
</body></html>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, *args):
        pass  # suppress logs


def start_server():
    """Start the local embed server (idempotent)."""
    global _server, _port
    if _server is not None:
        return _port

    _server = http.server.HTTPServer(('127.0.0.1', 0), _EmbedHandler)
    _port = _server.server_address[1]
    threading.Thread(target=_server.serve_forever, daemon=True).start()
    logger.info("[video] Embed server started on port %d", _port)
    return _port


def get_embed_url(video_url: str) -> str | None:
    """Get a local embed URL for a YouTube video."""
    video_id = _extract_video_id(video_url)
    if not video_id:
        return None
    port = start_server()
    return f"http://127.0.0.1:{port}/{video_id}"
