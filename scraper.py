import asyncio
import logging
import discord

log = logging.getLogger("scraper")

SCRAPE_TIMEOUT = 60


def _get_visible_channels(guild, limit=5):
    """grab text channels everyone can see — needed for sidebar scraping"""
    channels = []
    for ch in guild.text_channels:
        perms = ch.permissions_for(guild.default_role)
        if perms.read_messages:
            channels.append(ch)
        if len(channels) >= limit:
            break
    # fallback to first N channels if none are explicitly public
    if not channels:
        channels = guild.text_channels[:limit]
    return channels


async def scrape_members(guild, *, skip_bots=True):
    """get guild members via 3-tier fallback: cache → fetch_members → chunk"""
    members = []
    method = None

    # tier 1: gateway cache (populated if guild_subscriptions=True)
    cached = guild.members
    if cached and len(cached) > 1:
        members = list(cached)
        method = "cache"
        log.info(f"found {len(members)} members in cache")

    # tier 2: fetch_members (sidebar scrape via visible channels)
    if len(members) <= 1:
        channels = _get_visible_channels(guild)
        log.info(f"trying fetch_members with {len(channels)} channels...")
        try:
            members = await asyncio.wait_for(
                guild.fetch_members(
                    channels=channels or discord.utils.MISSING, delay=0.5
                ),
                timeout=SCRAPE_TIMEOUT,
            )
            method = "fetch_members"
        except asyncio.TimeoutError:
            log.warning(f"fetch_members timed out after {SCRAPE_TIMEOUT}s")
        except Exception as e:
            log.warning(f"fetch_members failed: {e}")

    # tier 3: gateway chunk (needs privs for large guilds)
    if not members:
        log.info("trying chunk (gateway request)...")
        try:
            members = await asyncio.wait_for(
                guild.chunk(),
                timeout=SCRAPE_TIMEOUT,
            )
            method = "chunk"
        except asyncio.TimeoutError:
            log.warning(f"chunk timed out after {SCRAPE_TIMEOUT}s")
        except Exception as e:
            log.warning(f"chunk failed: {e}")

    if not members:
        log.error("could not retrieve any members")
        return []

    total = len(members)
    bot_count = sum(1 for m in members if m.bot)

    if skip_bots:
        members = [m for m in members if not m.bot]

    log.info(
        f"scraped {total} members via {method} "
        f"({bot_count} bots, {len(members)} targets after filtering)"
    )
    return members
