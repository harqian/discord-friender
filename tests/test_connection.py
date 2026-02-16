"""test discord token login. connects, prints user info, lists guilds."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import discord
import config


def main():
    if not config.TOKEN:
        print("DISCORD_TOKEN not set in .env")
        return

    client = discord.Client()

    @client.event
    async def on_ready():
        print(f"logged in as: {client.user} (id={client.user.id})")
        print(f"guilds ({len(client.guilds)}):")
        for g in client.guilds:
            print(f"  {g.name} (id={g.id}, members={g.member_count})")
        await client.close()

    client.run(config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
