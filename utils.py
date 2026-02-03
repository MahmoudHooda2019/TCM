import csv
import os
import datetime


RESUME_FILE = "resume.txt"

# ── column layout ─────────────────────────────────────────────────────────────
# ID | Timestamp | Type | Status | Preview | Error
# Status lifecycle:  PENDING  →  SUCCESS | FAILED
# Every message that exists in the source channel appears here, regardless of
# whether it was actually sent.

HEADERS = ["MessageID", "Timestamp", "Type", "Status", "Preview", "Error"]


def init_resume():
    """Create resume file with headers if it does not already exist."""
    if not os.path.exists(RESUME_FILE):
        with open(RESUME_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(HEADERS)


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _classify(msg) -> str:
    """Return a short label for the message type."""
    if not getattr(msg, "media", None):
        return "text"
    cls = type(msg.media).__name__          # e.g. MessageMediaPhoto
    mapping = {
        "MessageMediaPhoto":    "photo",
        "MessageMediaDocument": "document",
        "MessageMediaWebPage":  "link",
        "MessageMediaVideo":    "video",
        "MessageMediaAudio":    "audio",
        "MessageMediaVoice":    "voice",
    }
    return mapping.get(cls, cls)


def _preview(msg, max_len=60) -> str:
    """One-line text snippet — safe for a TSV column."""
    raw = (getattr(msg, "text", "") or "").replace("\n", " ").strip()
    if not raw:
        return "(no text)"
    return raw[:max_len] + ("…" if len(raw) > max_len else "")


def log_pending(msg):
    """
    Write a PENDING row for *msg* the moment it is discovered in the history.
    This guarantees every source message appears in the file, even if the app
    crashes before attempting to send it.
    """
    with open(RESUME_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow([
            msg.id,
            _now(),
            _classify(msg),
            "PENDING",
            _preview(msg),
            ""
        ])


def update_status(message_id, status: str, error: str = ""):
    """
    Rewrite the file, changing the row that matches *message_id* to the new
    status / error.  Called exactly once per message after the send attempt.
    """
    rows = []
    with open(RESUME_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        rows = list(reader)          # first row is the header

    for row in rows[1:]:             # skip header
        if row[0] == str(message_id):
            row[3] = status          # Status column
            row[5] = error           # Error column
            break                    # only one match expected

    with open(RESUME_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerows(rows)


# kept for backward-compat with transfer.py caller ---------------------
def save_resume(message_id, status="SUCCESS", error=""):
    update_status(message_id, status, error)


def load_resume_ids() -> set:
    """Return set of message IDs that already have a SUCCESS status (skip them)."""
    if not os.path.exists(RESUME_FILE):
        return set()
    ids = set()
    with open(RESUME_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader, None)           # skip header
        for row in reader:
            if len(row) >= 4 and row[3] == "SUCCESS":
                ids.add(int(row[0]))
    return ids


def parse_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None
