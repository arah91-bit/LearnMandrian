"""Learner state — the durable memory of a good learning app.

One JSON file holds what the conversation window can't: the lesson plan, the
vocabulary with real spaced-repetition scheduling (SM-2), per-tone production
accuracy from tone-ear reads, session summaries, and the practice-day streak.
The tutor BRAIN maintains it through tools (see app.py TOOLS); the UI reads it
via /api/state; a compact snapshot is injected into the brain's system prompt
each turn so it always arrives knowing where Phil is.
"""
import contextlib
import contextvars
import datetime
import json
import os
import pathlib
import threading

import curriculum
import reader

DATA = pathlib.Path(os.environ.get("DATA_DIR", pathlib.Path(__file__).parent / "data"))

# Which learner this request belongs to. The auth middleware sets it from the
# session cookie; contextvars ride into uvicorn's thread pool with the
# request, so two users' turns can overlap without touching each other's
# files. None (tests, scripts) falls back to the legacy root-level layout.
_USER = contextvars.ContextVar("tutor_user", default=None)


def set_user(username):
    _USER.set(username)


def current_user():
    return _USER.get()


def user_dir():
    u = _USER.get()
    return DATA / "users" / u if u else DATA


def _state_file():
    return user_dir() / "state.json"

_DEFAULT = {
    "plan": {"focus": "", "next_up": [], "notes": ""},
    "vocab": [],          # {hanzi,pinyin,english,tones,added,reps,interval,ease,due,last_grade}
    "tone_stats": {},     # "expected_heard" -> count, e.g. "3_2": 4
    "sessions": [],       # {date, summary}
    "days": [],           # ISO dates with at least one turn
    "writing": {},        # char -> {times, best (fewest corrections), last}
    "settings": {         # display prefs — the UI reads these, the brain sees immersion
        "show_hanzi": True,
        "show_pinyin": True,
        "tone_display": "marks",     # marks | numbers
        "immersion": False,
    },
    "placement": None,    # {date, stage_idx, stage, per_stage} once taken
    "can_do": {},         # exit-check results: S1 -> {passed, lift_stage_idx, ...}
    "activity": [],       # self-study log: {date, kind, detail, score}
    "reader": {},         # graded reader: text_id -> {date, score}
    "tone_attempts": [],  # detailed tone history with target/heard/audio metadata
    "pulse": [],          # S7 fluency-pulse history: {date, n, sections..., holds}
    "pulse_open": None,   # a dealt-but-unfinished pulse accumulating its sections
}

_SETTING_KEYS = set(_DEFAULT["settings"])


def _today():
    return datetime.date.today().isoformat()


def load():
    f = _state_file()
    if f.exists():
        state = json.loads(f.read_text())
        for k, v in _DEFAULT.items():          # older state files gain new keys
            state.setdefault(k, json.loads(json.dumps(v)))
        return state
    return json.loads(json.dumps(_DEFAULT))


_LOCK = threading.RLock()


def save(state):
    f = _state_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")              # atomic: a crash never tears the file
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1))
    tmp.replace(f)


@contextlib.contextmanager
def txn():
    """load → mutate → save as one unit. Sync endpoints run on uvicorn's thread
    pool, so two quick actions (grade a review, flip a setting) can otherwise
    interleave read-modify-write and drop one. An exception inside skips the
    save. The brain keeps its own load/save (holding this lock across a
    multi-second LLM call would freeze every panel action; its window stays)."""
    with _LOCK:
        state = load()
        yield state
        save(state)


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
def log_tone_attempt(state, expected, heard, hanzi="", pinyin="", audio_path="", source=""):
    expected_tones = [int(t) for t in expected]
    heard_tones = [int(t) for t in heard]
    pairs = list(zip(expected_tones, heard_tones))
    for e, h in pairs:
        k = f"{e}_{h}"
        state["tone_stats"][k] = state["tone_stats"].get(k, 0) + 1
    if hanzi or pinyin or audio_path or source:
        state.setdefault("tone_attempts", []).append({
            "date": _today(),
            "target_hanzi": str(hanzi or ""),
            "target_pinyin": str(pinyin or ""),
            "expected": expected_tones,
            "heard": heard_tones,
            "audio": str(audio_path or ""),
            "source": str(source or ""),
        })
        state["tone_attempts"] = state["tone_attempts"][-200:]
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


def tone_drill_targets(state, n=5):
    """Recent missed words/syllables first; aggregate confusions as fallback."""
    out, seen = [], set()
    for a in reversed(state.get("tone_attempts", [])):
        expected, heard = a.get("expected") or [], a.get("heard") or []
        if not any(e != h for e, h in zip(expected, heard)):
            continue
        key = (a.get("target_hanzi", ""), tuple(expected), tuple(heard))
        if key in seen:
            continue
        seen.add(key)
        out.append({"hanzi": a.get("target_hanzi", ""),
                    "pinyin": a.get("target_pinyin", ""),
                    "expected": expected, "heard": heard,
                    "audio": a.get("audio", ""), "source": a.get("source", "")})
        if len(out) >= n:
            return out
    for c in top_confusions(state, n - len(out)):
        out.append({"hanzi": "", "pinyin": "",
                    "expected": [c["expected"]], "heard": [c["heard"]],
                    "count": c["count"], "audio": "", "source": "aggregate"})
    return out


# ── Handwriting-pad results (recorded by the app, not the brain) ──────────────
def record_writing(state, char, mistakes):
    w = state["writing"].setdefault(char, {"times": 0, "best": None, "last": None})
    w["times"] += 1
    w["best"] = mistakes if w["best"] is None else min(w["best"], mistakes)
    w["last"] = _today()


# ── Settings, placement, activity ──────────────────────────────────────────────
def update_settings(state, patch):
    s = state["settings"]
    for k, v in (patch or {}).items():
        if k not in _SETTING_KEYS:
            continue
        if k == "tone_display":
            s[k] = v if v in ("marks", "numbers") else "marks"
        else:
            s[k] = bool(v)
    return s


def set_placement(state, result):
    state["placement"] = {"date": _today(), **result}


def set_can_do(state, result):
    sid = result["stage"]
    state.setdefault("can_do", {})[sid] = {"date": _today(), **result}


def record_activity(state, kind, detail="", score=None):
    state["activity"].append(
        {"date": _today(), "kind": kind, "detail": detail, "score": score})
    state["activity"] = state["activity"][-60:]


# ── Stage & recommendations ────────────────────────────────────────────────────
def learned_count(state):
    """Words that have survived scheduling — two solid reps and a real interval."""
    return sum(1 for w in state["vocab"] if w["reps"] >= 2 and w["interval"] >= 3)


def speaking_stage(state):
    """App-derived position: vocab mastery, lifted by placement or can-do checks."""
    idx = curriculum.stage_for_learned(learned_count(state))
    if state.get("placement"):
        idx = max(idx, state["placement"]["stage_idx"])
    for res in state.get("can_do", {}).values():
        if res.get("passed"):
            idx = max(idx, int(res.get("lift_stage_idx", 0)))
    return idx


def writing_rung(state):
    """First rung whose fixed characters aren't all clean passes (best <= 1)."""
    wr = state["writing"]
    for r in curriculum.WRITING_RUNGS:
        if r["chars"] and any(not (wr.get(h) and wr[h]["best"] <= 1)
                              for h, _, _ in r["chars"]):
            return r["id"]
    return "W3"


def _did_today(state, *kinds):
    t = _today()
    return any(a["date"] == t and a["kind"] in kinds for a in state["activity"])


# ── The S7 fluency pulse ───────────────────────────────────────────────────────
# Fluency has no exit, so nothing above S7 to pass into — instead a recurring
# diagnostic measures drift: unseen reading, unseen listening, a 成语
# composition, one shadowed line. curriculum.py holds the reserve content;
# this side holds the rhythm (every PULSE_INTERVAL_DAYS) and the history.
def pulse_due(state):
    if speaking_stage(state) < 7:
        return False
    hist = state.get("pulse", [])
    if not hist:
        return True
    last = datetime.date.fromisoformat(hist[-1]["date"])
    return (datetime.date.today() - last).days >= curriculum.PULSE_INTERVAL_DAYS


def pulse_view(state):
    """The Progress card's payload: due-ness, cadence, recent history."""
    hist = state.get("pulse", [])
    days_since = None
    if hist:
        days_since = (datetime.date.today()
                      - datetime.date.fromisoformat(hist[-1]["date"])).days
    return {"at_stage": speaking_stage(state) >= 7,
            "due": pulse_due(state),
            "days_since": days_since,
            "interval_days": curriculum.PULSE_INTERVAL_DAYS,
            "history": hist[-12:][::-1]}


def pulse_start(state):
    """Deal the nth pulse and hold it open; sections land via pulse_record."""
    n = len(state.get("pulse", []))
    deal = curriculum.pulse_deal(n)
    state["pulse_open"] = {"date": _today(), "n": n,
                           "reading_id": deal["reading"]["id"],
                           "listening_id": deal["listening"]["id"],
                           "compose_id": deal["compose"]["id"],
                           "shadow_zh": deal["shadow"]["zh"],
                           "shadow_tones": deal["shadow"]["tones"],
                           "sections": {}}
    return deal


_PULSE_SECTIONS = ("reading", "listening", "compose", "shadow")

_PULSE_REMEDY = {
    "reading": {"id": "reading", "label": "读 — reading practice",
                "why": "Reading comprehension slipped — a passage run brings it back."},
    "listening": {"id": "listening", "label": "听 — listening practice",
                  "why": "Listening slipped — native-speed passages, little and often."},
    "compose": {"id": "compose", "label": "作 — write a composition",
                "why": "The 成语 composition didn't land — write one with the checker on."},
    "shadow": {"id": "tone_drill", "label": "声 — tone drill",
               "why": "Tones drifted while shadowing — drill the confusions directly."},
}


def _pulse_section_verdict(section, r):
    if section == "compose":
        return "holds" if r.get("passed") else "slipping"
    if section == "shadow":
        if r.get("skipped") or not r.get("total"):
            return "skipped"
        return curriculum.pulse_verdict(r["hits"] / r["total"])
    total = r.get("total") or 0
    return curriculum.pulse_verdict(r["right"] / total if total else 0)


def pulse_record(state, section, result):
    """Store one section's result (verdict attached); once all four are in,
    close the pulse: remediation for whatever decayed, an entry in history.
    Returns the finished report, or None while sections are still missing."""
    open_ = state.get("pulse_open")
    if not open_ or section not in _PULSE_SECTIONS:
        return None
    result = dict(result)
    result["verdict"] = _pulse_section_verdict(section, result)
    open_["sections"][section] = result
    if set(open_["sections"]) < set(_PULSE_SECTIONS):
        return None
    s = open_["sections"]
    report = {"date": open_["date"], "n": open_["n"],
              **{k: s[k] for k in _PULSE_SECTIONS}}
    report["remedy"] = [dict(_PULSE_REMEDY[k]) for k in _PULSE_SECTIONS
                        if s[k]["verdict"] in ("slipping", "decayed")]
    report["holds"] = sum(1 for k in _PULSE_SECTIONS if s[k]["verdict"] == "holds")
    state.setdefault("pulse", []).append(report)
    state["pulse"] = state["pulse"][-24:]          # a year of fortnights
    state["pulse_open"] = None
    record_activity(state, "pulse", f"pulse {open_['n'] + 1}",
                    f"{report['holds']}/4 hold")
    return report


def recommend(state):
    """The next best activity, deterministically, so 'what should I do?' always
    has one answer. Order: know where you stand → clear the debt (reviews) →
    balance the diet (reading/listening/writing) → new material (lesson)."""
    due = len(due_words(state))
    if state.get("placement") is None and len(state["vocab"]) < 5:
        return {"id": "placement", "title": "Take the placement test",
                "why": "Five minutes to find your level, so lessons start in the right place."}
    if due > 0:
        return {"id": "review", "title": f"Review {min(due, 8)} due word{'s' if due > 1 else ''}",
                "why": "Reviews come first, always — the schedule only works if you clear it."}
    if pulse_due(state):
        return {"id": "pulse", "title": "Take the fluency pulse",
                "why": "Every two weeks at S7: an unseen read, an unseen listen, a "
                       "成语 composition, one shadowed line — see what held and what slipped."}
    if not _did_today(state, "reading", "listening", "read"):
        nxt = reader.next_text(state, speaking_stage(state))
        if nxt:   # the graded reader outranks generic practice: it BUILDS vocabulary
            return {"id": "read", "tid": nxt["id"],
                    "title": f"Read: {nxt['title']} — {nxt['title_en']}",
                    "why": "The next text on your reading ladder — new words come with it."}
        last_practice = next((a["kind"] for a in reversed(state["activity"])
                              if a["kind"] in ("reading", "listening")), None)
        kind = "listening" if last_practice == "reading" else "reading"
        return {"id": kind, "title": f"{kind.capitalize()} practice",
                "why": f"No {kind} yet today — a few minutes keeps both channels moving."}
    if not _did_today(state, "lesson", "turn"):
        return {"id": "lesson", "title": "Continue the lesson",
                "why": "Reviews are clear and you've practiced — time for new material with the tutor."}
    cy = curriculum.chengyu_of_the_day()
    if cy["zh"] not in {w["hanzi"] for w in state["vocab"]}:
        return {"id": "chengyu", "title": f"成语 of the day: {cy['zh']}",
                "why": "Everything else is done — one four-character story into "
                       "the deck keeps the long tail growing."}
    return {"id": "writing", "title": "Writing practice",
            "why": "Everything else is done today — a few minutes at the pad locks characters in."}


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
    st = curriculum.STAGES[speaking_stage(state)]
    lines = [
        f"Date {_today()} · streak {streak(state)} day(s) · "
        f"{len(state['vocab'])} words tracked · {len(state['sessions'])} sessions so far",
        f"App-derived position: Speaking {st['id']} ({st['name']}, {st['hsk']}) · "
        f"Writing {writing_rung(state)}"
        + (f" · placed by test {state['placement']['date']}" if state.get("placement") else ""),
        f"Plan focus: {state['plan']['focus'] or '(none set — set one!)'}",
        f"Next up: {'; '.join(state['plan']['next_up']) or '(empty)'}",
    ]
    have = {w["hanzi"] for w in state["vocab"]}
    coming = [w for w in curriculum.SEEDS.get(st["id"], []) if w[0] not in have][:8]
    if coming:
        lines.append("Stage word-plan not yet taught: " + ", ".join(
            f"{hz} ({py}, {en})" for hz, py, en, _ in coming))
    last_read = next((a for a in reversed(state["activity"]) if a["kind"] == "read"), None)
    if last_read:
        text = reader.get_text(last_read.get("detail", ""))
        if text:
            lines.append(f"Last reader text: {text['title']} — {text['title_en']}")
    if state["settings"].get("immersion"):
        lines.append("Immersion mode is ON — he asked for as much Mandarin as his level allows.")
    if speaking_stage(state) >= 4:      # S4+: deal a conversation theme (see
        import datetime                  # curriculum.md's theme catalog)
        themes = curriculum.CONVERSATION_THEMES.get(st["id"], [])
        if themes:
            theme = themes[datetime.date.today().toordinal() % len(themes)]
            lines.append(f"Conversation theme of the day (S4+ catalog): {theme}")
    recent = [a for a in state["activity"] if a["kind"] != "turn"][-3:]
    if recent:
        lines.append("Recent self-study in the app: " + "; ".join(
            f"{a['date']} {a['kind']}" + (f" {a['score']}" if a.get("score") else "")
            + (f" ({a['detail']})" if a.get("detail") else "") for a in recent))
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
    stage_idx = speaking_stage(state)
    return {
        "plan": state["plan"],
        "vocab": sorted(state["vocab"], key=lambda w: (w["due"] > t, w["added"]),
                        reverse=False),
        "stats": {
            "streak": streak(state),
            "days_total": len(state["days"]),
            "sessions": len(state["sessions"]),
            "words_total": len(state["vocab"]),
            "learned": learned_count(state),
            "due_count": len(due_words(state)),
            "tone_accuracy": tone_accuracy(state),
            "confusions": top_confusions(state),
            "tone_targets": tone_drill_targets(state),
        },
        "sessions": state["sessions"][::-1][:10],
        "tone_recent": state.get("tone_attempts", [])[-6:][::-1],
        "activity_recent": [a for a in state["activity"]
                            if a["kind"] != "turn"][-8:][::-1],
        "writing": state["writing"],
        "settings": state["settings"],
        "position": {"stage_idx": stage_idx,
                     "stage": curriculum.STAGES[stage_idx]["id"],
                     "writing_rung": writing_rung(state),
                     "placement": state.get("placement"),
                     "can_do": state.get("can_do", {})},
        "pulse": pulse_view(state),
        "recommend": recommend(state),
        "today": t,
    }
