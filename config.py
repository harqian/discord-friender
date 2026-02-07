import os
import sys
from dotenv import load_dotenv

load_dotenv()


def _require(key):
    val = os.getenv(key)
    if not val:
        print(f"missing required env var: {key}")
        sys.exit(1)
    return val


def _int(key, default):
    return int(os.getenv(key, default))


def _bool(key, default):
    return os.getenv(key, default).lower() in ("true", "1", "yes")


TOKEN = _require("DISCORD_TOKEN")
GUILD_ID = int(_require("GUILD_ID"))

# rate limiting
REQUEST_DELAY_MIN = _int("REQUEST_DELAY_MIN", "30")
REQUEST_DELAY_MAX = _int("REQUEST_DELAY_MAX", "60")
BATCH_SIZE = _int("BATCH_SIZE", "20")
BATCH_PAUSE = _int("BATCH_PAUSE", "600")

# filtering
SKIP_BOTS = _bool("SKIP_BOTS", "true")
