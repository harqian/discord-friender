# discord-friender

userbot that sends friend requests to every member of a discord server.

> **⚠️ ToS warning**: this uses a user token (selfbot), which violates discord's ToS. your account can be banned. use a burner.

## how it works

```
1. log in with user token
2. connect to gateway, join target guild
3. scrape full member list from guild
4. send friend request to each member (with rate limiting)
5. log results (accepted, failed, already friends, etc)
```

## architecture

```
discord-friender/
├── main.py              # cli entrypoint
├── config.py            # settings / env loading
├── scraper.py           # guild member scraping
├── friender.py          # friend request sender w/ rate limiting
├── state.py             # persistence - track who we've already requested
├── requirements.txt
├── .env.example
└── SPEC.md
```

single process, async. no web server, no db — just a CLI tool.

## tech stack

| component | choice | why |
|-----------|--------|-----|
| language | python 3.11+ | best selfbot library ecosystem |
| selfbot lib | `discord.py-self` (dolfies fork) | actively maintained, supports user api endpoints |
| persistence | sqlite via `aiosqlite` | zero setup, tracks request state across runs |
| cli | `click` | simple arg parsing |
| config | `.env` + `python-dotenv` | keep token out of code |

## config

```env
# .env
DISCORD_TOKEN=your_user_token_here
GUILD_ID=123456789012345678

# rate limiting (conservative defaults)
REQUEST_DELAY_MIN=30        # min seconds between friend requests
REQUEST_DELAY_MAX=60        # max seconds (randomized within range)
BATCH_SIZE=20               # requests per batch before long pause
BATCH_PAUSE=600             # seconds to pause between batches (10 min)

# filtering
SKIP_BOTS=true              # don't try to friend bot accounts
SKIP_SELF=true              # obviously
```

## member scraping strategy

two approaches depending on guild size and permissions:

### approach 1: `guild.fetch_members()` (preferred)
- works if you can see the member list
- for guilds >1000 members, this scrapes the member sidebar
- only returns online/idle/dnd members unless you have elevated perms
- uses `MEMBER_SIDEBAR_SCRAPING_DELAY` internally

### approach 2: `guild.chunk()`
- requests full member list via gateway opcode 8
- works better if you have manage_guild or similar perms
- more complete but more detectable

the app tries approach 1 first, falls back to approach 2, logs which it used and how many members it found.

## friend request flow

```python
# pseudocode
async def friend_loop(members, state_db):
    for batch in chunk(members, BATCH_SIZE):
        for member in batch:
            if await state_db.already_requested(member.id):
                continue
            if member.bot and SKIP_BOTS:
                continue

            try:
                await member.send_friend_request()
                await state_db.mark_requested(member.id, status="sent")
                log.info(f"sent request to {member}")
            except discord.Forbidden:
                await state_db.mark_requested(member.id, status="forbidden")
                log.warn(f"forbidden: {member}")
            except discord.HTTPException as e:
                if e.status == 429:  # rate limited
                    retry_after = e.retry_after
                    log.warn(f"rate limited, sleeping {retry_after}s")
                    await asyncio.sleep(retry_after)
                    # retry this one
                else:
                    await state_db.mark_requested(member.id, status="error")
                    log.error(f"failed: {member} - {e}")

            delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
            await asyncio.sleep(delay)

        log.info(f"batch done, pausing {BATCH_PAUSE}s")
        await asyncio.sleep(BATCH_PAUSE)
```

## state persistence (sqlite)

```sql
CREATE TABLE friend_requests (
    user_id       TEXT PRIMARY KEY,
    username      TEXT,
    status        TEXT,  -- 'sent', 'forbidden', 'error', 'already_friends'
    requested_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

this means you can ctrl+c and resume later without re-requesting people.

## rate limiting strategy

discord doesn't publish exact limits for friend requests but community reports suggest:
- ~5-10 requests before soft throttling kicks in
- hard rate limit responses (429) include `retry_after`
- accounts sending too many requests too fast get flagged

our strategy is **extremely conservative**:
- 30-60s random delay between each request
- batches of 20, then 10min pause
- honor all 429 responses exactly
- jitter everything to look less automated

at these rates: ~500 members ≈ 8-12 hours. this is intentional.

## cli interface

```bash
# basic usage
python3 main.py

# dry run - scrape members and show count, don't send requests
python3 main.py --dry-run

# show progress / stats from previous runs
python3 main.py --stats

# resume from where we left off (default behavior, but explicit)
python3 main.py --resume

# override guild from cli
python3 main.py --guild 123456789012345678
```

## logging

stdout with levels. no log file by default (pipe to file if you want).

```
[INFO]  connected as user#1234
[INFO]  target guild: My Server (1234 members)
[INFO]  scraping members via fetch_members...
[INFO]  found 892 members (137 bots skipped)
[INFO]  755 members to request (42 already requested in previous run)
[INFO]  starting friend requests...
[INFO]  [1/713] sent request to alice#5678
[INFO]  [2/713] sent request to bob#9012
[WARN]  [3/713] forbidden: charlie#3456 (they have requests disabled)
[INFO]  sleeping 45s...
...
[INFO]  batch 1/36 complete, pausing 600s
```

## risks and mitigations

| risk | mitigation |
|------|------------|
| account ban | use a burner account. conservative rate limits. |
| phone verification trigger | may need a phone-verified account to send requests |
| captcha challenge | discord.py-self doesn't handle captchas. if hit, must solve manually or stop. |
| member list incomplete | log count discrepancy, warn user. try both scraping approaches. |
| token leaked | .env + .gitignore, never log the token |
| target user has requests disabled | catch Forbidden, log, move on |

## what's NOT in scope

- accepting incoming friend requests
- DM'ing users after friending
- multiple guilds in one run (just run it again with different GUILD_ID)
- proxy/IP rotation (overkill for this)
- captcha solving
