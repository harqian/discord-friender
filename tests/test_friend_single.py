"""send ONE friend request to a specific user ID.
watches for captcha trigger. use to test the full pipeline on a single target.

usage: act && python3 tests/test_friend_single.py USER_ID"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import logging
import discord
import config
import captcha

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("test_friend")


def main():
    if len(sys.argv) < 2:
        print("usage: python3 tests/test_friend_single.py USER_ID")
        return

    target_id = int(sys.argv[1])

    if not config.TOKEN:
        print("DISCORD_TOKEN not set in .env")
        return

    client = discord.Client(captcha_handler=captcha.solve_captcha)

    @client.event
    async def on_ready():
        log.info(f"logged in as {client.user}")

        try:
            user = await client.fetch_user(target_id)
            log.info(f"target: {user} (id={user.id})")

            log.info("sending friend request...")
            await user.send_friend_request()
            log.info("friend request sent successfully!")

        except discord.CaptchaRequired as e:
            log.error(f"captcha required and not auto-solved: {e}")
            for attr in dir(e):
                if not attr.startswith("_"):
                    log.info(f"  {attr} = {getattr(e, attr, '?')}")

        except discord.Forbidden as e:
            log.error(f"forbidden: {e}")

        except discord.HTTPException as e:
            log.error(f"http error: {e.status} {e.text}")

        except Exception as e:
            log.error(f"unexpected error: {type(e).__name__}: {e}")

        finally:
            await client.close()

    client.run(config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
