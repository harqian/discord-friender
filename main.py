import asyncio
import logging
import sys
import click
import discord
import config
import state
import scraper
import friender
import captcha

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
log = logging.getLogger("friender")


class FrienderClient(discord.Client):
    def __init__(self, guild_id, dry_run=False, **kwargs):
        super().__init__(**kwargs)
        self.guild_id = guild_id
        self.dry_run = dry_run

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
            members = await scraper.scrape_members(
                guild, skip_bots=config.SKIP_BOTS
            )

            if not members:
                log.error("no members found, exiting")
                return

            # filter out ourselves
            members = [m for m in members if m.id != self.user.id]

            if self.dry_run:
                already = 0
                for m in members:
                    if await state.already_requested(db, m.id):
                        already += 1
                log.info(f"dry run: {len(members)} targets, {already} already requested")
                return

            await friender.send_requests(
                members,
                db,
                self,
                delay_min=config.REQUEST_DELAY_MIN,
                delay_max=config.REQUEST_DELAY_MAX,
                batch_size=config.BATCH_SIZE,
                batch_pause=config.BATCH_PAUSE,
            )
        finally:
            await db.close()
            await self.close()


@click.command()
@click.option("--dry-run", is_flag=True, help="scrape members only, don't send requests")
@click.option("--stats", "show_stats", is_flag=True, help="show stats from previous runs and exit")
@click.option("--guild", type=int, default=None, help="override GUILD_ID from env")
def main(dry_run, show_stats, guild):
    guild_id = guild or config.GUILD_ID

    if show_stats:
        asyncio.run(_show_stats())
        return

    client = FrienderClient(guild_id, dry_run=dry_run, captcha_handler=captcha.solve_captcha)
    client.run(config.TOKEN, log_handler=None)


async def _show_stats():
    db = await state.init_db()
    stats = await state.get_stats(db)
    total = await state.get_total_requested(db)
    await db.close()

    if not stats:
        print("no requests recorded yet")
        return

    print(f"total: {total}")
    for status, count in sorted(stats.items()):
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()
