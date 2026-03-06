import asyncio
import random
import logging
import os
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, ChatWriteForbiddenError, UserBannedInChannelError

# ─── CONFIG ───────────────────────────────────────────────────────────────────

API_ID         = int(os.environ["API_ID"])
API_HASH       = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

GROUPS = [
    "eo_bf",
    "jt_ry",
]

# Your messages — one is picked at random each cycle
MESSAGES = [
    "Test"
]

# ─── TIMING CONFIG ────────────────────────────────────────────────────────────

# Fast interval between messages (seconds) — keep this as you need
MIN_INTERVAL = 10
MAX_INTERVAL = 30

# After this many messages, take a short breather (avoids flood triggers)
BURST_LIMIT    = 15
BURST_REST_MIN = 45    # seconds
BURST_REST_MAX = 90    # seconds

# Occasionally slip in a slightly longer pause (mimics human distraction)
LONG_PAUSE_CHANCE = 0.10    # 10% chance
LONG_PAUSE_MIN    = 60      # seconds
LONG_PAUSE_MAX    = 120     # seconds

# ─── LOGGING ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def pick_message(last_index: int | None) -> tuple[int, str]:
    """Pick a random message, avoiding repeating the last one."""
    available = [i for i in range(len(MESSAGES)) if i != last_index]
    index = random.choice(available)
    return index, MESSAGES[index]


async def human_delay():
    """Fast delay with slight gaussian jitter so timing never looks robotic."""
    base = random.uniform(MIN_INTERVAL, MAX_INTERVAL)
    jitter = random.gauss(0, base * 0.08)   # ±8% noise
    duration = max(MIN_INTERVAL * 0.8, base + jitter)
    log.info(f"Next message in {duration:.1f}s.")
    await asyncio.sleep(duration)


async def maybe_long_pause():
    """10% chance of a slightly longer pause to break the pattern."""
    if random.random() < LONG_PAUSE_CHANCE:
        duration = random.uniform(LONG_PAUSE_MIN, LONG_PAUSE_MAX)
        log.info(f"Short human pause for {duration:.0f}s.")
        await asyncio.sleep(duration)

# ─── MAIN LOOP ────────────────────────────────────────────────────────────────

async def run(client: TelegramClient):
    sent_count = 0
    last_index = None

    log.info(f"Starting fast message loop for {len(GROUPS)} groups.")

    while True:

        # ── Burst rest every N messages ──
        if sent_count > 0 and sent_count % BURST_LIMIT == 0:
            rest = random.uniform(BURST_REST_MIN, BURST_REST_MAX)
            log.info(f"[Burst limit reached] Resting {rest:.0f}s before continuing.")
            await asyncio.sleep(rest)

        for group in list(GROUPS):

            last_index, message = pick_message(last_index)

            try:
                await client.send_message(group, message)
                sent_count += 1
                log.info(f"[#{sent_count}] Sent to @{group}: \"{message}\"")

            except FloodWaitError as e:
                wait = e.seconds + random.randint(3, 10)
                log.warning(f"Flood wait — sleeping {wait}s.")
                await asyncio.sleep(wait)
                continue

            except (ChatWriteForbiddenError, UserBannedInChannelError):
                log.error(f"Access lost in @{group}. Removing from list.")
                GROUPS.remove(group)
                break

            except Exception as e:
                log.error(f"Unexpected error on @{group}: {e}. Waiting 30s.")
                await asyncio.sleep(30)
                continue

            # ── Fast delay between each message ──
            await human_delay()

        # ── Occasional longer pause after a full cycle ──
        await maybe_long_pause()

        if not GROUPS:
            log.error("No groups left to message. Shutting down.")
            break


async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    await client.connect()

    if not await client.is_user_authorized():
        log.error("Session is not authorized. Please regenerate your SESSION_STRING.")
        return

    log.info("Logged in successfully.")

    try:
        await run(client)
    except KeyboardInterrupt:
        log.info("Stopped by user.")
    finally:
        await client.disconnect()
        log.info("Disconnected.")


if __name__ == "__main__":
    asyncio.run(main())
