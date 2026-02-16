import asyncio
import logging
import time
import config
from nopecha.api.urllib import UrllibAPIClient

log = logging.getLogger("captcha")

DISCORD_HCAPTCHA_SITEKEY = "a9b5fb07-92ff-493f-86fe-352a2803b3df"
MAX_RETRIES = 3


def _make_client():
    """create nopecha client with sane retry limits.
    defaults are 10 POST / 120 GET attempts which can hang for ages."""
    return UrllibAPIClient(
        config.NOPECHA_KEY,
        post_max_attempts=5,
        get_max_attempts=30,
    )


async def solve_captcha(exception, client) -> str:
    """solve hcaptcha via nopecha API. called automatically by discord.py-self
    when a CaptchaRequired is raised."""

    if not config.NOPECHA_KEY:
        log.error("NOPECHA_KEY not set, can't solve captcha")
        raise exception

    # extract what we can from the exception
    sitekey = getattr(exception, "sitekey", None) or DISCORD_HCAPTCHA_SITEKEY
    rqdata = getattr(exception, "rqdata", None)
    rqtoken = getattr(exception, "rqtoken", None)
    user_agent = getattr(client, "user_agent", None)

    log.info(
        f"captcha triggered — sitekey={sitekey[:16]}... "
        f"rqdata={'yes' if rqdata else 'no'} rqtoken={'yes' if rqtoken else 'no'}"
    )

    # build request body
    body = {
        "type": "hcaptcha",
        "sitekey": sitekey,
        "url": "https://discord.com",
    }

    data = {}
    if rqdata:
        data["rqdata"] = rqdata
    if user_agent:
        data["useragent"] = user_agent

    # optional proxy
    proxy_url = config.get_proxy_url()
    if proxy_url:
        data["proxy"] = proxy_url
        log.info(f"using proxy: {config.PROXY_SCHEME}://{config.PROXY_HOST}:{config.PROXY_PORT}")

    if data:
        body["data"] = data

    for attempt in range(1, MAX_RETRIES + 1):
        nopecha_client = _make_client()
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(nopecha_client.solve_raw, body),
                timeout=120,
            )
            elapsed = time.monotonic() - start

            # solve_raw returns dict like {"data": "token_string"}
            token = result.get("data", result) if isinstance(result, dict) else result
            if isinstance(token, str):
                log.info(f"solved in {elapsed:.1f}s (attempt {attempt}/{MAX_RETRIES}, token length={len(token)})")
                return token
            else:
                log.error(f"unexpected result in {elapsed:.1f}s: {result}")

        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start
            log.error(f"timeout after {elapsed:.1f}s (attempt {attempt}/{MAX_RETRIES})")
        except Exception as e:
            elapsed = time.monotonic() - start
            log.error(f"solve failed in {elapsed:.1f}s (attempt {attempt}/{MAX_RETRIES}): {e}")

        if attempt < MAX_RETRIES:
            await asyncio.sleep(2)

    log.error("all captcha solve attempts failed")
    raise exception
