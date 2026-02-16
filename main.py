import asyncio
import logging
import sys
import click
import discord
import config
import state
import scraper
import friender
from friender import SKIP_RELATIONSHIP_TYPES
import captcha

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("main")


class FrienderClient(discord.Client):
    def __init__(self, guild_id, *, dry_run=False, limit=None, **kwargs):
        super().__init__(**kwargs)
        self.guild_id = guild_id
        self.dry_run = dry_run
        self.limit = limit

    async def on_ready(self):
        log.info(f"connected as {self.user}")

        guild = self.get_guild(self.guild_id)
        if not guild:
            log.error(f"guild {self.guild_id} not found — are you a member?")
            await self.close()
            return

        log.info(f"target guild: {guild.name} ({guild.member_count} members)")

        db = await state.init_db()

        try:
            members = await scraper.scrape_members(guild, skip_bots=config.SKIP_BOTS)
            if not members:
                log.error("no members found")
                return

            # filter out ourselves
            members = [m for m in members if m.id != self.user.id]

            if self.dry_run:
                # check both state db and live relationship cache
                would_send = 0
                skipped = 0
                for m in members[:50]:
                    in_db = await state.already_requested(db, m.id)
                    rel = self.get_relationship(m.id)
                    rel_type = rel.type if rel else None

                    if in_db:
                        tag = "[db]"
                    elif rel_type and rel_type in SKIP_RELATIONSHIP_TYPES:
                        tag = f"[{rel_type.name}]"
                    else:
                        tag = "[send]"
                        would_send += 1

                    if tag != "[send]":
                        skipped += 1

                    log.info(f"  {tag:20s} {m} (id={m.id})")

                if len(members) > 50:
                    log.info(f"  ... and {len(members) - 50} more")
                log.info(f"dry run: {len(members)} total, {would_send} would send, {skipped} skipped")
                return

            await friender.send_requests(
                members,
                db,
                self,
                delay_min=config.REQUEST_DELAY_MIN,
                delay_max=config.REQUEST_DELAY_MAX,
                batch_size=config.BATCH_SIZE,
                batch_pause=config.BATCH_PAUSE,
                limit=self.limit,
            )
        finally:
            await db.close()
            await self.close()


@click.command()
@click.option("--dry-run", is_flag=True, help="scrape only, show targets")
@click.option("--stats", "show_stats", is_flag=True, help="show previous run stats")
@click.option("--guild", type=int, default=None, help="override GUILD_ID from env")
@click.option("--limit", type=int, default=None, help="max number of requests to send")
@click.option("--test-captcha", is_flag=True, help="run captcha test only")
def main(dry_run, show_stats, guild, limit, test_captcha):
    guild_id = guild or config.GUILD_ID

    if show_stats:
        asyncio.run(_show_stats())
        return

    if test_captcha:
        _run_captcha_test()
        return

    if not config.TOKEN:
        log.error("DISCORD_TOKEN not set in .env")
        sys.exit(1)

    if not guild_id:
        log.error("GUILD_ID not set — use --guild or set in .env")
        sys.exit(1)

    client = FrienderClient(
        guild_id,
        dry_run=dry_run,
        limit=limit,
        captcha_handler=captcha.solve_captcha,
    )
    client.run(config.TOKEN, log_handler=None)


async def _show_stats():
    db = await state.init_db()
    stats = await state.get_stats(db)
    total = await state.get_total_requested(db)
    cap = await state.get_captcha_stats(db)
    await db.close()

    if not stats:
        print("no requests recorded yet")
        return

    print(f"total: {total}")
    for status, count in sorted(stats.items()):
        print(f"  {status}: {count}")
    print(f"\ncaptcha stats:")
    print(f"  clean (no captcha): {cap['clean']}")
    print(f"  captcha triggered:  {cap['captcha']}")


def _run_captcha_test():
    """quick inline captcha test"""
    import tests.test_captcha_discord as t
    asyncio.run(t.main())


if __name__ == "__main__":
    main()
