"""Learner state — the durable memory of a good learning app.

One JSON file holds what the conversation window can't: the lesson plan, the
vocabulary with real spaced-repetition scheduling (SM-2), per-tone production
accuracy from tone-ear reads, session summaries, and the practice-day streak.
The tutor BRAIN maintains it through tools (see app.py TOOLS); the UI reads it
via /api/state; a compact snapshot is injected into the brain's system prompt
each turn so it always arrives knowing where Phil is.
"""
import datetime
import json
import os
import pathlib

DATA = pathlib.Path(os.environ.get("DATA_DIR", pathlib.Path(__file__).parent / "data"))
STATE_FILE = DATA / "state.json"

_DEFAULT = {
    "plan": {"focus": "", "next_up": [], "notes": ""},
    "vocab": [],          # {hanzi,pinyin,english,tones,added,reps,interval,ease,due,last_grade}
    "tone_stats": {},     # "expected_heard" -> count, e.g. "3_2": 4
    "sessions": [],       # {date, summary}
    "days": [],           # ISO dates with at least one turn
}


def _today():
    return datetime.date.today().isoformat()


def load():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return json.loads(json.dumps(_DEFAULT))


def save(state):
    DATA.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1))


def touch_day(state):
    t = _today()
    if t not in state["days"]:
        state["days"].append(t)
        state["days"] = sorted(state["days"])[-365:]


def streak(state):
    days = set(state["days"])
    day = datetime.date.today()
    if day.isoformat() not in days:          # today not practiced yet — count from yesterday
        day -= datetime.timedelta(days=1)
    n = 0
    while day.isoformat() in days:
        n += 1
        day -= datetime.timedelta(days=1)
    return n


# ── Vocabulary / SM-2 ──────────────────────────────────────────────────────────
def add_word(state, hanzi, pinyin, english, tones):
    for w in state["vocab"]:
        if w["hanzi"] == hanzi:
            return f"{hanzi} is already in the vocab list"
    state["vocab"].append({
        "hanzi": hanzi, "pinyin": pinyin, "english": english,
        "tones": [int(t) for t in tones],
        "added": _today(), "reps": 0, "interval": 0, "ease": 2.5,
        "due": _today(), "last_grade": None,
    })
    return f"added {hanzi} ({pinyin}) — due for review today"


def grade_word(state, hanzi, grade):
    grade = max(0, min(5, int(grade)))
    for w in state["vocab"]:
        if w["hanzi"] != hanzi:
            continue
        if grade < 3:
            w["reps"], w["interval"] = 0, 0          # relearn: due again today
        else:
            w["reps"] += 1
            w["interval"] = 1 if w["reps"] == 1 else 3 if w["reps"] == 2 else round(w["interval"] * w["ease"])
            w["ease"] = max(1.3, w["ease"] + 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
        w["due"] = (datetime.date.today() + datetime.timedelta(days=w["interval"])).isoformat()
        w["last_grade"] = grade
        return f"{hanzi} graded {grade}; next review in {w['interval']} day(s)"
    return f"{hanzi} is not in the vocab list — add_word it first"


def due_words(state):
    t = _today()
    return [w for w in state["vocab"] if w["due"] <= t]


# ── Tone production stats ──────────────────────────────────────────────────────
def log_tone_attempt(state, expected, heard):
    pairs = list(zip([int(t) for t in expected], [int(t) for t in heard]))
    for e, h in pairs:
        k = f"{e}_{h}"
        state["tone_stats"][k] = state["tone_stats"].get(k, 0) + 1
    hits = sum(1 for e, h in pairs if e == h)
    return f"logged {len(pairs)} syllable(s), {hits} on target"


def tone_accuracy(state):
    acc = {}
    for t in (1, 2, 3, 4):
        total = sum(n for k, n in state["tone_stats"].items() if k.startswith(f"{t}_"))
        good = state["tone_stats"].get(f"{t}_{t}", 0)
        acc[t] = {"correct": good, "total": total}
    return acc


def top_confusions(state, n=3):
    offs = [(k.split("_"), c) for k, c in state["tone_stats"].items()
            if k.split("_")[0] != k.split("_")[1]]
    offs.sort(key=lambda x: -x[1])
    return [{"expected": int(e), "heard": int(h), "count": c} for (e, h), c in offs[:n]]


# ── Plan & sessions ────────────────────────────────────────────────────────────
def update_plan(state, focus=None, next_up=None, notes=None):
    if focus is not None:
        state["plan"]["focus"] = focus
    if next_up is not None:
        if isinstance(next_up, str):    # a model WILL pass a bare string eventually
            next_up = [next_up]         # (it did — list() exploded it into letters)
        state["plan"]["next_up"] = [str(x) for x in next_up][:8]
    if notes is not None:
        state["plan"]["notes"] = notes
    return "plan updated"


def end_session(state, summary):
    state["sessions"].append({"date": _today(), "summary": summary})
    state["sessions"] = state["sessions"][-30:]
    return "session recorded"


# ── Views ──────────────────────────────────────────────────────────────────────
def snapshot(state):
    """Compact per-turn context for the tutor brain."""
    due = due_words(state)
    acc = tone_accuracy(state)
    acc_line = "  ".join(
        f"T{t}:{v['correct']}/{v['total']}" for t, v in acc.items() if v["total"])
    lines = [
        f"Date {_today()} · streak {streak(state)} day(s) · "
        f"{len(state['vocab'])} words tracked · {len(state['sessions'])} sessions so far",
        f"Plan focus: {state['plan']['focus'] or '(none set — set one!)'}",
        f"Next up: {'; '.join(state['plan']['next_up']) or '(empty)'}",
    ]
    if state["plan"]["notes"]:
        lines.append(f"Notes to self: {state['plan']['notes']}")
    if due:
        lines.append("Due for review now: " + ", ".join(
            f"{w['hanzi']} ({w['pinyin']}, {w['english']})" for w in due[:10]))
    else:
        lines.append("Nothing due for review.")
    if acc_line:
        lines.append(f"Tone production so far: {acc_line}")
    if state["sessions"]:
        lines.append(f"Last session: {state['sessions'][-1]['summary']}")
    return "\n".join(lines)


def api_view(state):
    """Everything the UI panels render."""
    t = _today()
    return {
        "plan": state["plan"],
        "vocab": sorted(state["vocab"], key=lambda w: (w["due"] > t, w["added"]),
                        reverse=False),
        "stats": {
            "streak": streak(state),
            "days_total": len(state["days"]),
            "sessions": len(state["sessions"]),
            "words_total": len(state["vocab"]),
            "due_count": len(due_words(state)),
            "tone_accuracy": tone_accuracy(state),
            "confusions": top_confusions(state),
        },
        "sessions": state["sessions"][::-1][:10],
        "today": t,
    }
