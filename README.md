# discord-friender

Automation for sending Discord friend requests from members of a target guild.

It uses `discord.py-self` for user-account automation, stores request state in SQLite (`friend_requests.db`), and optionally solves hCaptcha via NopeCHA.

## Setup

```bash
uv sync
cp .env.example .env
```

Fill `.env`:

- `DISCORD_TOKEN` (user token)
- `GUILD_ID` (target server id)
- `NOPECHA_KEY` (required if captchas appear)

## Run

```bash
# preview targets only
uv run python main.py --dry-run

# send a small batch first
uv run python main.py --limit 5

# show sqlite stats from previous runs
uv run python main.py --stats

# test captcha solver only
uv run python main.py --test-captcha
```

## Config knobs

Rate controls from `.env`:

- `REQUEST_DELAY_MIN` / `REQUEST_DELAY_MAX`
- `BATCH_SIZE`
- `BATCH_PAUSE`
- `SKIP_BOTS`

Optional captcha proxy:

- `PROXY_SCHEME`, `PROXY_HOST`, `PROXY_PORT`, `PROXY_USER`, `PROXY_PASS`

## Notes

- The scraper tries member discovery in this order: cache -> `fetch_members` -> `chunk`.
- Every attempt is recorded in SQLite with status + error details.
- Start with `--dry-run` and low limits before larger runs.
