import asyncio

from telethon import TelegramClient
from InquirerPy import inquirer

from ui import print_banner, print_message, print_section
from transfer import transfer_messages
import config


# ── input helpers ─────────────────────────────────────────────────────────────

def _ask_api():
    """Return (api_id: int, api_hash: str).  Loops until both are valid."""
    print_section("Telegram API credentials")
    print("  You can create/manage your Telegram API keys at:")
    print("    https://my.telegram.org")
    print()
    while True:
        try:
            api_id   = int(input("  API ID   : "))
            api_hash = input("  API Hash : ").strip()
            if not api_hash:
                raise ValueError("API Hash is empty")
            print_message("  ✓ Credentials saved.", color="green")
            return api_id, api_hash
        except Exception as e:
            print_message(f"  ✗ {e}  — try again.", color="red")


def _ask_channels():
    """Return (old_channel, new_channel) — non-empty strings."""
    print_section("Channel links")
    while True:
        old = input("  Old channel link : ").strip()
        if old:
            break
        print_message("  ✗ Old channel link cannot be empty.", color="red")

    while True:
        new = input("  New channel link : ").strip()
        if new:
            break
        print_message("  ✗ New channel link cannot be empty.", color="red")

    return old, new


def _ask_content_type() -> str:
    print_section("Content type")
    return inquirer.select(
        message="  Transfer:",
        choices=["all", "text", "media"],
        pointer="  ▶"
    ).execute()


def _ask_delay() -> float:
    print_section("Delay")
    while True:
        try:
            val = float(input("  Delay between messages (seconds) [1]: ") or "1")
            if val < 0:
                raise ValueError
            print_message(f"  ✓ Delay set to {val}s", color="green")
            return val
        except (ValueError, TypeError):
            print_message("  ✗ Enter a number ≥ 0.", color="red")


def _confirm(old_ch, new_ch, content_type, delay) -> bool:
    """Print a summary and ask the user to confirm."""
    print_section("Ready to transfer")
    print(f"    Source      : {old_ch}")
    print(f"    Destination : {new_ch}")
    print(f"    Content     : {content_type}")
    print(f"    Delay       : {delay}s")
    print()
    return inquirer.confirm(
        message="  Start transfer?",
        default=True
    ).execute()


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print_banner()

    # ── collect everything up-front ───────────────────────────────────────────
    api_id, api_hash   = _ask_api()
    old_channel, new_channel = _ask_channels()
    content_type       = _ask_content_type()
    delay              = _ask_delay()

    # Patch config so transfer.py picks up the delay value
    config.delay_seconds = delay

    # ── confirm & go ──────────────────────────────────────────────────────────
    if not _confirm(old_channel, new_channel, content_type, delay):
        print_message("\n  Cancelled.", color="yellow")
        return

    client = TelegramClient("TCM_session", api_id, api_hash)
    print()
    asyncio.run(transfer_messages(
        client=client,
        old_channel=old_channel,
        new_channel=new_channel,
        content_type=content_type,
    ))


if __name__ == "__main__":
    main()
