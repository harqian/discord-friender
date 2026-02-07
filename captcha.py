import asyncio
import logging
import webbrowser
import tempfile
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

log = logging.getLogger("friender")

DISCORD_HCAPTCHA_SITEKEY = "a9b5fb07-92ff-493f-86fe-352a2803b3df"
LOCAL_PORT = 9831

# solved token gets stored here by the callback
_solved_token = None
_solve_event = None


def _make_captcha_html(sitekey, rqdata=None):
    """html page that renders hcaptcha widget and posts solution back to us.
    nopecha extension auto-solves it in the browser."""
    rqdata_attr = f'data-rqdata="{rqdata}"' if rqdata else ""
    return f"""<!DOCTYPE html>
<html>
<head><title>solve captcha</title></head>
<body style="display:flex;justify-content:center;align-items:center;height:100vh;margin:0;font-family:sans-serif;background:#1a1a2e;color:#eee;">
<div style="text-align:center;">
    <p>waiting for nopecha to solve...</p>
    <div id="captcha-container"></div>
    <script src="https://js.hcaptcha.com/1/api.js?onload=onLoad&render=explicit" async defer></script>
    <script>
    function onLoad() {{
        hcaptcha.render('captcha-container', {{
            sitekey: '{sitekey}',
            {f"'rqdata': '{rqdata}'," if rqdata else ""}
            callback: function(token) {{
                fetch('http://localhost:{LOCAL_PORT}/solved?token=' + encodeURIComponent(token));
            }}
        }});
    }}
    </script>
</div>
</body>
</html>"""


class _CaptchaHandler(BaseHTTPRequestHandler):
    """tiny http server that serves the captcha page and receives the solution"""

    def do_GET(self):
        global _solved_token

        if self.path.startswith("/solved?token="):
            # extract token from query string
            token = self.path.split("token=", 1)[1]
            from urllib.parse import unquote
            _solved_token = unquote(token)
            _solve_event.set()

            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            # serve the captcha page
            sitekey = getattr(self.server, "_sitekey", DISCORD_HCAPTCHA_SITEKEY)
            rqdata = getattr(self.server, "_rqdata", None)
            html = _make_captcha_html(sitekey, rqdata)

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass  # suppress http server logs


async def solve_captcha(exception, client):
    """solve captcha by opening local page in browser.
    nopecha extension auto-solves hcaptcha, then posts token back to us."""
    global _solved_token, _solve_event

    _solved_token = None
    _solve_event = threading.Event()

    sitekey = getattr(exception, "_sitekey", None) or DISCORD_HCAPTCHA_SITEKEY
    rqdata = getattr(exception, "rqdata", None)
    service = getattr(exception, "service", "unknown")

    log.warning(f"captcha required! service={service}")

    # start local http server in a thread
    server = HTTPServer(("127.0.0.1", LOCAL_PORT), _CaptchaHandler)
    server._sitekey = sitekey
    server._rqdata = rqdata
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # open in chrome specifically — thats where nopecha is installed
    url = f"http://localhost:{LOCAL_PORT}/"
    log.info(f"opening captcha page in chrome: {url}")
    import subprocess
    subprocess.Popen(["open", "-a", "Google Chrome", url])

    # wait for the extension to solve and post back
    loop = asyncio.get_event_loop()
    try:
        await asyncio.wait_for(
            loop.run_in_executor(None, _solve_event.wait),
            timeout=120,
        )
    except asyncio.TimeoutError:
        log.error("captcha solve timed out after 120s")
        server.shutdown()
        raise exception
    finally:
        server.shutdown()

    if not _solved_token:
        log.error("no captcha token received")
        raise exception

    # close the chrome tab via applescript
    _close_captcha_tab()

    log.info("captcha solved via browser!")
    return _solved_token


def _close_captcha_tab():
    """close the localhost captcha tab in chrome via applescript"""
    import subprocess
    script = f'''
    tell application "Google Chrome"
        set windowList to every window
        repeat with w in windowList
            set tabList to every tab of w
            repeat with t in tabList
                if URL of t contains "localhost:{LOCAL_PORT}" then
                    close t
                end if
            end repeat
        end repeat
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    except Exception:
        pass
