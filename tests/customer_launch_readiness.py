"""Read-only checks of public deployment availability and reported Stripe mode.

Never signs in, creates accounts/checkouts, sends mail or changes configuration.
Provider inbox receipt is deliberately not asserted by this public check.
"""
import concurrent.futures
import json
import urllib.request
from pathlib import Path

ORIGIN = "https://nonprofitboardbuilder.com"
PATHS = ("/", "/recruit", "/board-fundraising-game", "/strategic-planning", "/board-recommitment", "/api", "/api/payments/config")


def check(path):
    try:
        request = urllib.request.Request(ORIGIN + path, headers={"User-Agent": "BoardBuilder-ReadOnly-Launch-Check"})
        with urllib.request.urlopen(request, timeout=15) as response:
            data = response.read()
            row = {"path": path, "status": response.status, "available": response.status == 200}
            if path == "/api/payments/config":
                config = json.loads(data)
                row["stripe_mode"] = config.get("stripe_mode", "unknown")
                row["legacy_paid_programs_enabled"] = config.get("paid_programs_live")
            return row
    except Exception as exc:
        return {"path": path, "available": False, "error": str(exc)[:200]}


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(check, PATHS))
    result = {"origin": ORIGIN, "read_only": True, "public_checks": rows,
              "public_pages_available": all(row["available"] for row in rows),
              "stripe_live_mode_reported": any(row.get("stripe_mode") == "live" for row in rows),
              "provider_credentials_verified": False, "live_email_receipt_verified": False,
              "deployment_commit_verified": False}
    Path("test_reports").mkdir(exist_ok=True)
    Path("test_reports/current-public-launch-readiness.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
