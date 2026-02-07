import asyncio
import logging
import random
import discord
import state

log = logging.getLogger("friender")


SKIP_RELATIONSHIP_TYPES = {
    discord.RelationshipType.friend,
    discord.RelationshipType.outgoing_request,
    discord.RelationshipType.incoming_request,
    discord.RelationshipType.blocked,
}


async def send_requests(
    members,
    db,
    client,
    *,
    delay_min=30,
    delay_max=60,
    batch_size=20,
    batch_pause=600,
):
    # filter out ourselves, existing relationships, and already-requested
    targets = []
    skipped_db = 0
    skipped_rel = 0
    for m in members:
        if m.id == client.user.id:
            continue
        if await state.already_requested(db, m.id):
            skipped_db += 1
            continue
        # check if already friends, pending, or blocked
        rel = client.get_relationship(m.id)
        if rel and rel.type in SKIP_RELATIONSHIP_TYPES:
            await state.mark_requested(db, m.id, str(m), rel.type.name)
            skipped_rel += 1
            log.info(f"skipping {m}: already {rel.type.name}")
            continue
        targets.append(m)

    log.info(
        f"{len(targets)} to request "
        f"({skipped_db} already done in previous runs, "
        f"{skipped_rel} existing relationships skipped)"
    )

    if not targets:
        log.info("nothing to do")
        return

    sent = 0
    failed = 0
    total = len(targets)

    for i, member in enumerate(targets):
        # batch pause
        if i > 0 and i % batch_size == 0:
            batch_num = i // batch_size
            total_batches = (total + batch_size - 1) // batch_size
            log.info(f"batch {batch_num}/{total_batches} done, pausing {batch_pause}s")
            await asyncio.sleep(batch_pause)

        try:
            await member.send_friend_request()
            await state.mark_requested(db, member.id, str(member), "sent")
            sent += 1
            log.info(f"[{i+1}/{total}] sent to {member}")

        except discord.Forbidden:
            await state.mark_requested(db, member.id, str(member), "forbidden")
            failed += 1
            log.warning(f"[{i+1}/{total}] forbidden: {member}")

        except discord.HTTPException as e:
            if e.status == 429:
                # respect the retry_after from discord
                retry = getattr(e, "retry_after", 60)
                log.warning(f"rate limited, sleeping {retry}s")
                await asyncio.sleep(retry)
                # retry this member
                try:
                    await member.send_friend_request()
                    await state.mark_requested(db, member.id, str(member), "sent")
                    sent += 1
                    log.info(f"[{i+1}/{total}] sent to {member} (after retry)")
                except Exception as e2:
                    await state.mark_requested(db, member.id, str(member), "error")
                    failed += 1
                    log.error(f"[{i+1}/{total}] retry failed for {member}: {e2}")
            else:
                await state.mark_requested(db, member.id, str(member), "error")
                failed += 1
                log.error(f"[{i+1}/{total}] failed: {member} - {e}")

        except Exception as e:
            await state.mark_requested(db, member.id, str(member), "error")
            failed += 1
            log.error(f"[{i+1}/{total}] unexpected error for {member}: {e}")

        delay = random.uniform(delay_min, delay_max)
        await asyncio.sleep(delay)

    log.info(f"done. sent={sent}, failed={failed}, total={total}")
