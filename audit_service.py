import time
import json
import sqlite3
from ledger import LedgerEngine


def run_audit_service():
    print("--- 42 Bank Audit Service Starting ---")
    print("Monitoring Ledger Change Feed for suspicious activity...")

    last_id = 0
    # Initialize DB connection to check current max ID
    with sqlite3.connect("data/bank.db") as conn:
        row = conn.execute("SELECT MAX(id) FROM change_feed").fetchone()
        if row and row[0]:
            last_id = row[0]

    try:
        while True:
            with sqlite3.connect("data/bank.db") as conn:
                conn.row_factory = sqlite3.Row
                changes = conn.execute(
                    "SELECT * FROM change_feed WHERE id > ? ORDER BY id ASC", (last_id,)
                ).fetchall()

                for change in changes:
                    last_id = change["id"]
                    event_type = change["event_type"]
                    payload = json.loads(change["payload"])

                    # Simulated Agentic Logic: Auditor oversight
                    username = payload.get("username", "Unknown")
                    balance = payload.get("balance", 0.0)

                    print(
                        f"[AUDIT] Event #{last_id}: {event_type} - User: {username}, Balance: ${balance:.2f}"
                    )

                    # Logic: Alert on high balance or suspicious activity
                    if balance > 5000:
                        print(f"!!! ALERT: High value account detected: {username}")

            time.sleep(2)  # Polling interval
    except KeyboardInterrupt:
        print("\nAudit Service Stopped.")


if __name__ == "__main__":
    run_audit_service()
