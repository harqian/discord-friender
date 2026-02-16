"""test nopecha with discord's actual hcaptcha sitekey.
this is the critical test — if this works, captcha solving should work
for real friend requests. tests with and without proxy.

uses nopecha client directly for lower timeouts and visible polling."""

import asyncio
import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(name)s: %(message)s")

import config
from nopecha.api.urllib import UrllibAPIClient

DISCORD_SITEKEY = "a9b5fb07-92ff-493f-86fe-352a2803b3df"


def make_client():
    return UrllibAPIClient(
        config.NOPECHA_KEY,
        post_max_attempts=5,
        get_max_attempts=30,
    )


async def solve_with_proxy(proxy_url=None):
    body = {
        "type": "hcaptcha",
        "sitekey": DISCORD_SITEKEY,
        "url": "https://discord.com",
    }
    if proxy_url:
        body["data"] = {"proxy": proxy_url}
        print(f"  using proxy: {proxy_url}")

    client = make_client()
    start = time.monotonic()
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(client.solve_raw, body),
            timeout=120,
        )
        elapsed = time.monotonic() - start
        token = result.get("data", result) if isinstance(result, dict) else result
        if isinstance(token, str):
            print(f"  success in {elapsed:.1f}s, token length={len(token)}")
            return token
        else:
            print(f"  result in {elapsed:.1f}s: {result}")
            return None
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - start
        print(f"  timed out after {elapsed:.1f}s")
        return None
    except Exception as e:
        elapsed = time.monotonic() - start
        print(f"  failed after {elapsed:.1f}s: {type(e).__name__}: {e}")
        return None


async def main():
    if not config.NOPECHA_KEY:
        print("NOPECHA_KEY not set in .env")
        return

    # phase 1: no proxy
    print("phase 1: discord sitekey, no proxy")
    token = await solve_with_proxy(None)

    if token:
        print(f"\nphase 1 succeeded — captcha solving works without proxy")
        return

    # phase 2: with proxy (if configured)
    proxy_url = config.get_proxy_url()
    if proxy_url:
        print(f"\nphase 2: discord sitekey, with proxy")
        token = await solve_with_proxy(proxy_url)
        if token:
            print(f"\nphase 2 succeeded — captcha solving works WITH proxy")
            return
        print("\nphase 2 also failed")
    else:
        print("\nno proxy configured, skipping phase 2")
        print("set PROXY_* vars in .env to test with proxy")

    print("\nboth phases failed — may need browser-based approach")


if __name__ == "__main__":
    asyncio.run(main())
