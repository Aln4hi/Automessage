import asyncio
import random
import logging
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, ChatWriteForbiddenError, UserBannedInChannelError

# ─── CONFIG ───────────────────────────────────────────────────────────────────

API_ID         = int(os.environ["API_ID"])
API_HASH       = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

GROUPS = [
    "eo_bf",
    "BH_YF",
]

# Your messages — one is picked at random each cycle
MESSAGES = [
    "منو تجي اتفل بكسها واغلط عليها وانيجها تجي خاص",
    " اذا كسج يحكج وشهوتج صاعدة وصايرة نار دزي نقطة اشوفج شي حلو",
    "دزي نقطة وادزلج مقطع جاي انيج بصاحبتي بالشقة",
    "اذا فاطرة دزي نقطة خل اركبج واخلي كسج يغرك من النيج"
]

# ─── TIMING CONFIG ────────────────────────────────────────────────────────────

# Delay between sending to each group (seconds)
MIN_INTERVAL = 10
MAX_INTERVAL = 30

# After all groups have been messaged, wait before next full cycle
CYCLE_REST_MIN = 10
CYCLE_REST_MAX = 30

# After this many full cycles, take a short breather
BURST_LIMIT    = 15
BURST_REST_MIN = 45
BURST_REST_MAX = 90

# 10% chance of a longer pause after a full cycle
LONG_PAUSE_CHANCE = 0.10
LONG_PAUSE_MIN    = 60
LONG_PAUSE_MAX    = 120

# ─── LOGGING ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def pick_message(last_index):
    available = [i for i in range(len(MESSAGES)) if i != last_index]
    index = random.choice(available)
    return index, MESSAGES[index]


async def human_delay(min_s, max_s):
    base = random.uniform(min_s, max_s)
    jitter = random.gauss(0, base * 0.08)
    duration = max(min_s * 0.8, base + jitter)
    log.info(f"Waiting {duration:.1f}s.")
    await asyncio.sleep(duration)

# ─── MAIN LOOP ────────────────────────────────────────────────────────────────

async def run(client: TelegramClient):
    cycle_count = 0
    last_index = None
    active_groups = list(GROUPS)

    log.info(f"Starting message loop for {len(active_groups)} groups.")

    while True:

        cycle_count += 1
        log.info(f"─── Cycle #{cycle_count} ───")

        # ── Burst rest every N cycles ──
        if cycle_count > 1 and (cycle_count - 1) % BURST_LIMIT == 0:
            rest = random.uniform(BURST_REST_MIN, BURST_REST_MAX)
            log.info(f"[Burst rest] Pausing {rest:.0f}s after {BURST_LIMIT} cycles.")
            await asyncio.sleep(rest)

        # ── Send to EVERY group in this cycle ──
        for group in list(active_groups):

            last_index, message = pick_message(last_index)

            try:
                await client.send_message(group, message)
                log.info(f"[Cycle #{cycle_count}] Sent to @{group}: \"{message}\"")

            except FloodWaitError as e:
                wait = e.seconds + random.randint(3, 10)
                log.warning(f"Flood wait — sleeping {wait}s.")
                await asyncio.sleep(wait)
                # Still try to send to remaining groups after flood wait
                continue

            except (ChatWriteForbiddenError, UserBannedInChannelError):
                log.error(f"Access lost in @{group}. Removing from list.")
                active_groups.remove(group)
                continue

            except Exception as e:
                log.error(f"Unexpected error on @{group}: {e}. Waiting 30s.")
                await asyncio.sleep(30)
                continue

            # ── Short delay between groups within same cycle ──
            if group != active_groups[-1]:  # Don't delay after the last group
                await human_delay(MIN_INTERVAL, MAX_INTERVAL)

        # ── Rest between full cycles ──
        if random.random() < LONG_PAUSE_CHANCE:
            pause = random.uniform(LONG_PAUSE_MIN, LONG_PAUSE_MAX)
            log.info(f"[Long pause] {pause:.0f}s before next cycle.")
            await asyncio.sleep(pause)
        else:
            await human_delay(CYCLE_REST_MIN, CYCLE_REST_MAX)

        if not active_groups:
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
