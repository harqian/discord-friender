"""test member scraping on the target guild.
connects, scrapes members, prints count and sample names."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import discord
import config
import scraper


def main():
    if not config.TOKEN or not config.GUILD_ID:
        print("DISCORD_TOKEN and GUILD_ID must be set in .env")
        return

    client = discord.Client()

    @client.event
    async def on_ready():
        guild = client.get_guild(config.GUILD_ID)
        if not guild:
            print(f"guild {config.GUILD_ID} not found")
            await client.close()
            return

        print(f"target guild: {guild.name} ({guild.member_count} members)")

        members = await scraper.scrape_members(guild, skip_bots=config.SKIP_BOTS)
        print(f"\nscraped {len(members)} members")

        for m in members[:20]:
            print(f"  {m} (id={m.id}, bot={m.bot})")
        if len(members) > 20:
            print(f"  ... and {len(members) - 20} more")

        await client.close()

    client.run(config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
