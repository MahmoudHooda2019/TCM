# ── TCM – Telegram Channel Migrator ──────────────────────────────────────────
# Runtime values here are overwritten by main.py before transfer starts.
# They exist so that transfer.py can do  `import config; config.delay_seconds`
# and always see the latest value.

delay_seconds = 1            # patched at runtime
resume_file   = "resume.txt" # TSV – every source message is logged here
