import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
NOPECHA_KEY = os.getenv("NOPECHA_KEY", "")

# rate limiting
REQUEST_DELAY_MIN = int(os.getenv("REQUEST_DELAY_MIN", "30"))
REQUEST_DELAY_MAX = int(os.getenv("REQUEST_DELAY_MAX", "60"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "20"))
BATCH_PAUSE = int(os.getenv("BATCH_PAUSE", "600"))

SKIP_BOTS = os.getenv("SKIP_BOTS", "true").lower() == "true"

# optional proxy config for captcha solving
PROXY_SCHEME = os.getenv("PROXY_SCHEME", "")
PROXY_HOST = os.getenv("PROXY_HOST", "")
PROXY_PORT = os.getenv("PROXY_PORT", "")
PROXY_USER = os.getenv("PROXY_USER", "")
PROXY_PASS = os.getenv("PROXY_PASS", "")


def get_proxy_url():
    """build proxy url from parts, or return None if not configured"""
    if not PROXY_HOST:
        return None
    auth = ""
    if PROXY_USER:
        auth = f"{PROXY_USER}:{PROXY_PASS}@" if PROXY_PASS else f"{PROXY_USER}@"
    scheme = PROXY_SCHEME or "socks5"
    port = f":{PROXY_PORT}" if PROXY_PORT else ""
    return f"{scheme}://{auth}{PROXY_HOST}{port}"
