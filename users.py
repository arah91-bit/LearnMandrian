"""User accounts — the smallest multi-user layer that keeps the app honest.

users.json in the data mount holds every account: username -> scrypt-hashed
password (per-user salt) and a display name the tutor addresses the learner
by. Each user's learner state and conversation live under DATA/users/<name>/
(learner.py resolves paths through the per-request user contextvar); the
hanzi stroke cache, Tone Perfect clips and library index stay shared — they
are corpus, not progress.

First boot after the single-user era: bootstrap() sees no users.json, creates
TUTOR_USER (with TUTOR_USER_NAME as display name) from the existing
TUTOR_PASSWORD, and adopts the legacy root-level state/conversation files
into that user's directory — the original learner keeps every word.

Manage accounts from the container or host:
    python users.py add <username> [--name "Display Name"]   (prompts password)
    python users.py passwd <username>
    python users.py list
    python users.py remove <username>
"""
import argparse
import datetime
import getpass
import hashlib
import hmac
import json
import os
import pathlib
import re
import secrets

DATA = pathlib.Path(os.environ.get("DATA_DIR", pathlib.Path(__file__).parent / "data"))
USERS_FILE = DATA / "users.json"
_USERNAME_RE = re.compile(r"^[a-z0-9_-]{2,30}$")   # cookie-safe: no ':', no case games

_cache = {"mtime": None, "data": {}}


def _hash(password, salt_hex):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex),
                          n=2**14, r=8, p=1).hex()


def load_users():
    """users.json, cached on mtime — read on every request by the auth layer."""
    try:
        mtime = USERS_FILE.stat().st_mtime_ns
    except FileNotFoundError:
        return {}
    if _cache["mtime"] != mtime:
        _cache["data"] = json.loads(USERS_FILE.read_text())
        _cache["mtime"] = mtime
    return _cache["data"]


def save_users(users):
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = USERS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(users, ensure_ascii=False, indent=1))
    tmp.replace(USERS_FILE)
    _cache["mtime"] = None


def add(username, password, name=None):
    username = username.strip().lower()
    if not _USERNAME_RE.match(username):
        raise ValueError("username must be 2-30 chars of a-z 0-9 _ -")
    if len(password) < 6:
        raise ValueError("password must be at least 6 characters")
    users = dict(load_users())
    if username in users:
        raise ValueError(f"user {username} already exists")
    salt = secrets.token_hex(16)
    users[username] = {"salt": salt, "pw": _hash(password, salt),
                       "name": (name or username).strip(),
                       "created": datetime.date.today().isoformat()}
    save_users(users)
    (DATA / "users" / username).mkdir(parents=True, exist_ok=True)
    return users[username]


def set_password(username, password):
    users = dict(load_users())
    if username not in users:
        raise ValueError(f"no user {username}")
    if len(password) < 6:
        raise ValueError("password must be at least 6 characters")
    salt = secrets.token_hex(16)
    users[username].update(salt=salt, pw=_hash(password, salt))
    save_users(users)


def verify(username, password):
    """True only for a known user with the right password; constant-time compare."""
    rec = load_users().get(str(username).strip().lower())
    if not rec:
        return False
    return hmac.compare_digest(_hash(password, rec["salt"]), rec["pw"])


def display_name(username):
    rec = load_users().get(username or "")
    return rec["name"] if rec else "the learner"


def bootstrap():
    """One-time upgrade from the single-user era (no users.json yet): create
    TUTOR_USER from TUTOR_PASSWORD and adopt the legacy root-level data files.
    Idempotent — the moment users.json exists this never runs again."""
    if USERS_FILE.exists():
        return None
    password = os.environ.get("TUTOR_PASSWORD")
    if not password:
        return None
    username = os.environ.get("TUTOR_USER", "learner").strip().lower()
    add(username, password, os.environ.get("TUTOR_USER_NAME", username))
    udir = DATA / "users" / username
    moved = []
    for fname in ("state.json", "conversation.json", "conversation.prev.json"):
        legacy = DATA / fname
        if legacy.exists():
            legacy.rename(udir / fname)
            moved.append(fname)
    return {"user": username, "adopted": moved}


def main():
    ap = argparse.ArgumentParser(description="LanguageTutor accounts")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_add = sub.add_parser("add")
    p_add.add_argument("username")
    p_add.add_argument("--name", help="display name the tutor uses")
    p_pw = sub.add_parser("passwd")
    p_pw.add_argument("username")
    sub.add_parser("list")
    p_rm = sub.add_parser("remove")
    p_rm.add_argument("username")
    args = ap.parse_args()
    if args.cmd == "list":
        for u, rec in sorted(load_users().items()):
            print(f"{u}  ({rec['name']}, since {rec['created']})")
    elif args.cmd == "add":
        add(args.username, getpass.getpass("password: "), args.name)
        print(f"added {args.username}")
    elif args.cmd == "passwd":
        set_password(args.username, getpass.getpass("new password: "))
        print("password changed — existing sessions are signed out")
    elif args.cmd == "remove":
        users = dict(load_users())
        users.pop(args.username, None)
        save_users(users)
        print(f"removed {args.username} (their data dir is kept: "
              f"{DATA / 'users' / args.username})")


if __name__ == "__main__":
    main()
