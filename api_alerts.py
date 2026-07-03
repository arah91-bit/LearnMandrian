"""Operator paging when an API key runs out of credits.

Same billing signatures as LifeLog's llm.py (keep the two lists in sync — this repo
copies scaffolding rather than sharing a library). Any script/app code that calls a
paid API wraps the error path with `page_if_billing(service, err)`: if the error is a
billing failure it pages Pushbullet (PUSHBULLET_TOKEN) and returns True, at most once
per service per window (stamp file survives reruns). Zero dependencies by design.
"""
import json
import os
import pathlib
import time
import urllib.request

STAMPS = pathlib.Path(__file__).parent / ".api_alert_stamps.json"
WINDOW_HOURS = 6
_BILLING_MARKERS = ("credit balance", "insufficient_quota", "exceeded your current quota",
                    "billing hard limit", "payment required", "account is not active",
                    "billing_not_active", "credits are depleted", "insufficient balance")


def is_billing_error(e) -> bool:
    s = str(e).lower()
    return any(m in s for m in _BILLING_MARKERS)


def _pushbullet(title, body):
    token = os.environ.get("PUSHBULLET_TOKEN")
    if not token:
        return
    req = urllib.request.Request(
        "https://api.pushbullet.com/v2/pushes",
        data=json.dumps({"type": "note", "title": title, "body": body}).encode(),
        headers={"Access-Token": token, "Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10).read()


def page_if_billing(service, err) -> bool:
    """Page the operator if `err` is an out-of-credits failure. Safe to call in any
    except block: never raises, returns whether the error was a billing failure."""
    try:
        if not is_billing_error(err):
            return False
        stamps = json.loads(STAMPS.read_text()) if STAMPS.exists() else {}
        now = time.time()
        if now - stamps.get(service, 0) >= WINDOW_HOURS * 3600:
            stamps[service] = now
            STAMPS.write_text(json.dumps(stamps))
            _pushbullet("LanguageTutor: API credits",
                        f"The {service} API is out of credits — top up to keep going. "
                        f"({str(err)[:140]})")
        return True
    except Exception:
        return True  # detection said billing; never let paging break the caller
