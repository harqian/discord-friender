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
    limit=None,
):
    # filter: skip self, existing relationships, and already-requested
    targets = []
    skipped_db = 0
    skipped_rel = 0
    for m in members:
        if m.id == client.user.id:
            continue
        if await state.already_requested(db, m.id):
            skipped_db += 1
            continue
        rel = client.get_relationship(m.id)
        if rel and rel.type in SKIP_RELATIONSHIP_TYPES:
            await state.mark_requested(db, m.id, str(m), rel.type.name)
            skipped_rel += 1
            continue
        targets.append(m)

    if limit and len(targets) > limit:
        targets = targets[:limit]
        log.info(f"limiting to {limit} targets")

    if not targets:
        log.info(f"nothing to do ({skipped_db} already done, {skipped_rel} existing rels)")
        return

    sample = ", ".join(str(m) for m in targets[:10])
    if len(targets) > 10:
        sample += f" and {len(targets) - 10} more"
    log.info(
        f"{len(targets)} to request "
        f"({skipped_db} already done, {skipped_rel} existing rels): {sample}"
    )

    sent = 0
    failed = 0
    captcha_count = 0
    total = len(targets)
    current_delay_min = delay_min
    current_delay_max = delay_max

    for i, member in enumerate(targets):
        # batch pause
        if i > 0 and i % batch_size == 0:
            batch_num = i // batch_size
            total_batches = (total + batch_size - 1) // batch_size
            log.info(f"batch {batch_num}/{total_batches} done, pausing {batch_pause}s")
            await asyncio.sleep(batch_pause)

        try:
            # discord.py-self auto-calls captcha_handler if CaptchaRequired
            await member.send_friend_request()
            await state.mark_requested(db, member.id, str(member), "sent")
            sent += 1
            log.info(f"[{i+1}/{total}] sent to {member}")

        except discord.CaptchaRequired as e:
            # captcha_handler was called but either failed or wasn't set up
            captcha_count += 1
            await state.mark_requested(
                db, member.id, str(member), "captcha_failed",
                detail=str(e), captcha=True,
            )
            failed += 1
            log.error(f"[{i+1}/{total}] captcha not solved: {member}")

            # adaptive: if captchas appearing, slow down
            current_delay_min = min(current_delay_min * 1.5, 120)
            current_delay_max = min(current_delay_max * 1.5, 180)
            log.warning(f"increasing delays to {current_delay_min:.0f}-{current_delay_max:.0f}s")

        except discord.Forbidden:
            await state.mark_requested(db, member.id, str(member), "forbidden")
            failed += 1
            log.warning(f"[{i+1}/{total}] forbidden: {member}")

        except discord.HTTPException as e:
            if e.status == 429:
                retry = getattr(e, "retry_after", 60)
                log.warning(f"rate limited, sleeping {retry}s")
                await asyncio.sleep(retry)
                # retry once
                try:
                    await member.send_friend_request()
                    await state.mark_requested(db, member.id, str(member), "sent")
                    sent += 1
                    log.info(f"[{i+1}/{total}] sent to {member} (after retry)")
                except Exception as e2:
                    await state.mark_requested(
                        db, member.id, str(member), "rate_limited",
                        detail=f"retry also failed: {e2}",
                    )
                    failed += 1
                    log.error(f"[{i+1}/{total}] retry failed: {member}: {e2}")
            else:
                await state.mark_requested(
                    db, member.id, str(member), "error",
                    detail=f"{e.status}: {e.text}",
                )
                failed += 1
                log.error(f"[{i+1}/{total}] http error for {member}: {e.status} {e.text}")

        except Exception as e:
            await state.mark_requested(
                db, member.id, str(member), "error",
                detail=str(e),
            )
            failed += 1
            log.error(f"[{i+1}/{total}] unexpected: {member}: {e}")

        delay = random.uniform(current_delay_min, current_delay_max)
        await asyncio.sleep(delay)

    log.info(
        f"done. sent={sent} failed={failed} total={total} "
        f"captchas_triggered={captcha_count}"
    )
