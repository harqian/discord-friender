import asyncio
import logging
import discord

log = logging.getLogger("friender")

SCRAPE_TIMEOUT = 60


def _get_visible_channels(guild, limit=5):
    """grab text channels that everyone can see, for sidebar scraping"""
    channels = []
    for ch in guild.text_channels:
        everyone = guild.default_role
        perms = ch.permissions_for(everyone)
        if perms.read_messages:
            channels.append(ch)
        if len(channels) >= limit:
            break
    if not channels:
        channels = guild.text_channels[:limit]
    return channels


async def scrape_members(guild, *, skip_bots=True):
    """get guild members. tries cache first, then fetch_members, then chunk."""
    members = []
    method = None

    # the lib auto-subscribes guilds on connect (guild_subscriptions=True)
    # so by the time on_ready fires, members may already be cached
    cached = guild.members
    if cached and len(cached) > 1:
        members = list(cached)
        method = "cache"
        log.info(f"found {len(members)} members in cache")

    # if cache is thin, try fetch_members with explicit channels
    if len(members) <= 1:
        channels = _get_visible_channels(guild)
        if channels:
            log.info(f"using channels for scrape: {[c.name for c in channels]}")

        try:
            log.info("trying fetch_members (sidebar scrape)...")
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

    # last resort — gateway chunk, needs elevated perms for large guilds
    if not members:
        try:
            log.info("trying chunk (gateway request)...")
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
        f"got {total} members via {method} "
        f"({bot_count} bots, {len(members)} targets after filtering)"
    )
    return members
