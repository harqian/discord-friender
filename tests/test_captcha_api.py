"""test nopecha API with a public demo hcaptcha sitekey.
this confirms the API key works and basic connectivity is fine,
without touching discord at all.

uses the nopecha client directly so we can set lower max_attempts
and see whats happening instead of hanging forever."""

import asyncio
import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# enable nopecha's debug logging so we can see the polling
logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(name)s: %(message)s")

import config
from nopecha.api.urllib import UrllibAPIClient


async def main():
    if not config.NOPECHA_KEY:
        print("NOPECHA_KEY not set in .env")
        return

    # use the client directly so we can control retry limits
    # default is 120 GET attempts which can take forever
    client = UrllibAPIClient(
        config.NOPECHA_KEY,
        post_max_attempts=5,
        get_max_attempts=30,
    )

    body = {
        "type": "hcaptcha",
        "sitekey": "a5f74b19-9e45-40e0-b45d-47ff91b7a6c2",
        "url": "https://accounts.hcaptcha.com/demo",
    }

    print("solving public hcaptcha demo (max 30 poll attempts)...")
    start = time.monotonic()

    try:
        # run in thread since the urllib client is sync and blocks
        result = await asyncio.wait_for(
            asyncio.to_thread(client.solve_raw, body),
            timeout=120,
        )
        elapsed = time.monotonic() - start
        print(f"\nsuccess in {elapsed:.1f}s")
        # solve_raw returns a dict with "data" key
        token = result.get("data", result) if isinstance(result, dict) else result
        if isinstance(token, str):
            print(f"token length: {len(token)}")
            print(f"token prefix: {token[:50]}...")
        else:
            print(f"result: {result}")

    except asyncio.TimeoutError:
        elapsed = time.monotonic() - start
        print(f"\ntimed out after {elapsed:.1f}s")
    except Exception as e:
        elapsed = time.monotonic() - start
        print(f"\nfailed after {elapsed:.1f}s: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
