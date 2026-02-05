import asyncio
import random
import re
import sys
import time

from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest, ImportChatInviteRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from colorama import Fore, Style

import config
from utils import log_pending, save_resume, load_resume_ids, init_resume


# ── helpers ───────────────────────────────────────────────────────────────────

def _msg_text(msg) -> str:
    """
    Safely get the human text from a Telegram message, whether it is:
      - pure text
      - media with caption
    Different Telethon versions use .message / .raw_text / .text.
    """
    return (
        getattr(msg, "message", None)
        or getattr(msg, "raw_text", None)
        or getattr(msg, "text", None)
        or ""
    )


# ── invite hash ───────────────────────────────────────────────────────────────

def extract_invite_hash(link: str) -> str:
    link = link.strip().rstrip("/")
    match = re.search(r"(?:joinchat/|/\+|\+)([A-Za-z0-9_-]+)", link)
    if match:
        return match.group(1)
    bare = link.split("/")[-1]
    return bare if bare else ""


# ── channel resolver ──────────────────────────────────────────────────────────

async def _resolve_channel(client: TelegramClient, link: str, label: str):
    try:
        return await client.get_entity(link)
    except (ValueError, Exception):
        pass

    invite_hash = extract_invite_hash(link)
    if not invite_hash:
        print(Fore.RED + f"  ✗ Could not extract invite hash from {label}: '{link}'" + Style.RESET_ALL)
        return None
    try:
        updates = await client(ImportChatInviteRequest(invite_hash))
        entity  = updates.chats[0]
        print(Fore.GREEN + f"  ✓ Joined {label} successfully!" + Style.RESET_ALL)
        return entity
    except Exception as e:
        print(Fore.RED + f"  ✗ Cannot access {label}: {e}" + Style.RESET_ALL)
        return None


# ── progress bar ──────────────────────────────────────────────────────────────
# Prints on a SINGLE line that never scrolls.  Errors are collected and printed
# AFTER the bar finishes so they don't break the line.

class ProgressBar:
    """
    A self-contained, single-line progress bar.

        ── transferring ──────────────────────────────
         [████████████░░░░░░░░░░░░░░░░░░]  12 / 30  40%
         ✓ 10   ✗ 1   ⟳ 1   ▸ 1.2 msg/s
        ───────────────────────────────────────────────
    """

    BAR_WIDTH = 30                          # characters inside [ … ]

    def __init__(self, total: int):
        self.total    = total
        self.done     = 0                   # success + failed + skipped combined
        self.success  = 0
        self.failed   = 0
        self.skipped  = 0
        self.start_ts = None                # set on first tick, not here
        self._errors  = []                  # (msg_id, error_str)  – printed at end

        # header line (printed once)
        print()
        print(Fore.CYAN + "  ── transferring ──────────────────────────────" + Style.RESET_ALL)

    # ── public API ────────────────────────────────────────────────────────────

    def _stamp(self):
        """Set start_ts once, on the very first tick."""
        if self.start_ts is None:
            self.start_ts = time.time()

    def tick_success(self):
        self._stamp()
        self.done    += 1
        self.success += 1
        self._render()

    def tick_failed(self, msg_id, error: str):
        self._stamp()
        self.done   += 1
        self.failed += 1
        self._errors.append((msg_id, error))
        self._render()

    def tick_skipped(self):
        self._stamp()
        self.done    += 1
        self.skipped += 1
        self._render()

    def finish(self):
        """Call once after the loop.  Prints errors (if any) then summary."""
        self._render(force=True)
        print()                             # move off the bar line

        # ── errors collected during transfer ──────────────────────────────
        if self._errors:
            print(Fore.RED + "  ── errors ──────────────────────────────────" + Style.RESET_ALL)
            for msg_id, err in self._errors:
                print(Fore.RED + f"    ✗ msg {msg_id}: {err}" + Style.RESET_ALL)
            print()

        # ── summary ───────────────────────────────────────────────────────
        print(Fore.CYAN + "  ── summary ─────────────────────────────────" + Style.RESET_ALL)
        print(Fore.GREEN  + f"    ✓ Success : {self.success}" + Style.RESET_ALL)
        print(Fore.RED    + f"    ✗ Failed  : {self.failed}"  + Style.RESET_ALL)
        print(Fore.YELLOW + f"    ⟳ Skipped : {self.skipped}" + Style.RESET_ALL)
        elapsed = (time.time() - self.start_ts) if self.start_ts else 0.0
        if elapsed > 0 and self.success > 0:
            print(Fore.CYAN + f"    ▸ Speed   : {self.success / elapsed:.1f} msg/s  ({elapsed:.0f}s total)" + Style.RESET_ALL)
        print(Fore.CYAN + "    ▸ Resume saved to resume.txt" + Style.RESET_ALL)

    # ── rendering ─────────────────────────────────────────────────────────────

    def _render(self, force=False):
        pct      = self.done / self.total if self.total else 1.0
        filled   = int(self.BAR_WIDTH * pct)
        bar      = "█" * filled + "░" * (self.BAR_WIDTH - filled)
        elapsed   = (time.time() - self.start_ts) if self.start_ts else 0.0
        # need ≥ 2 ticks before showing speed so tick-1 microsecond spike is hidden
        speed_str = f"{self.done / elapsed:.1f}/s" if (elapsed > 0 and self.done >= 2) else "…"

        line = (
            f"  {Fore.CYAN}[{bar}]{Style.RESET_ALL}"
            f"  {Fore.WHITE}{self.done:>4} / {self.total:<4}{Style.RESET_ALL}"
            f"  {Fore.GREEN}{int(pct * 100):>3}%{Style.RESET_ALL}"
            f"  {Fore.GREEN}✓{self.success}{Style.RESET_ALL}"
            f" {Fore.RED}✗{self.failed}{Style.RESET_ALL}"
            f" {Fore.YELLOW}⟳{self.skipped}{Style.RESET_ALL}"
            f"  {Fore.CYAN}▸ {speed_str}{Style.RESET_ALL}"
        )

        # trailing spaces wipe any leftover chars from a previously longer line
        sys.stdout.write("\r" + line + "    ")
        sys.stdout.flush()


# ── fetch ALL messages in correct (oldest-first) order ───────────────────────

async def _fetch_all_sorted(client: TelegramClient, peer) -> list:
    """
    Page through GetHistoryRequest (newest-first, descending by ID).
    Collect every message, then reverse the whole list so we get
    strict oldest-first order before returning.
    """
    all_msgs  = []
    offset_id = 0          # 0 = start from the very newest
    limit     = 100

    print(Fore.CYAN + "  ── fetching messages …" + Style.RESET_ALL, end="", flush=True)

    while True:
        history = await client(GetHistoryRequest(
            peer=peer,
            offset_id=offset_id,
            offset_date=0,
            add_offset=0,
            limit=limit,
            max_id=0,
            min_id=0,
            hash=0
        ))

        if not history.messages:
            break

        all_msgs.extend(history.messages)
        # next page: start just below the oldest ID we got this round
        offset_id = history.messages[-1].id

        sys.stdout.write(f"\r  {Fore.CYAN}  fetching …  {len(all_msgs)} messages so far …{Style.RESET_ALL}")
        sys.stdout.flush()

    # Reverse → oldest first (ascending by ID)
    all_msgs.reverse()

    print(f"\r  {Fore.CYAN}  fetched {len(all_msgs)} messages total.{Style.RESET_ALL}         ")
    return all_msgs


# ── main transfer ─────────────────────────────────────────────────────────────

async def transfer_messages(client: TelegramClient, old_channel: str, new_channel: str,
                            content_type: str = "all"):

    await client.start()

    old = await _resolve_channel(client, old_channel, "old channel")
    if old is None:
        return
    new = await _resolve_channel(client, new_channel, "new channel")
    if new is None:
        return

    # ── 1.  Fetch everything first, sorted oldest→newest ─────────────────────
    all_messages = await _fetch_all_sorted(client, old)
    if not all_messages:
        print(Fore.YELLOW + "\n  Channel is empty — nothing to transfer." + Style.RESET_ALL)
        return

    # ── 2.  Resume setup ──────────────────────────────────────────────────────
    init_resume()
    already_done = load_resume_ids()

    # ── 3.  Progress bar (total is known now) ────────────────────────────────
    bar = ProgressBar(total=len(all_messages))

    # ── 4.  Walk messages in order ────────────────────────────────────────────
    for msg in all_messages:

        # log every message as PENDING the instant we see it
        log_pending(msg)

        # already transferred in a previous run → skip
        if msg.id in already_done:
            save_resume(msg.id, "SKIPPED")
            bar.tick_skipped()
            continue

        # ── attempt send ────────────────────────────────────────────────────
        try:
            sent = False

            text_content = _msg_text(msg)

            # media (photo / document / video / audio) + caption (إن وُجد)
            if content_type in ("media", "all") and msg.media and isinstance(
                msg.media, (MessageMediaPhoto, MessageMediaDocument)
            ):
                await client.send_file(new, msg.media, caption=text_content or "")
                sent = True

            # text-only messages
            if content_type in ("text", "all") and text_content and not sent:
                await client.send_message(new, text_content)
                sent = True

            # link / webpage embeds
            if content_type in ("media", "all") and msg.media and not sent:
                webpage = getattr(msg.media, "webpage", None)
                url     = getattr(webpage, "url", "") if webpage else ""
                if url:
                    caption = f"{text_content}\n{url}" if text_content else url
                    await client.send_message(new, f"[Link] {caption}")

            save_resume(msg.id, "SUCCESS")
            bar.tick_success()

        except Exception as e:
            save_resume(msg.id, "FAILED", str(e))
            bar.tick_failed(msg.id, str(e))

        # jittered delay
        jitter = config.delay_seconds * random.uniform(0.5, 1.5)
        await asyncio.sleep(jitter)

    # ── 5.  Done ──────────────────────────────────────────────────────────────
    bar.finish()
