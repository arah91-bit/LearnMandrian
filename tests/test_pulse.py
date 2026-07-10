"""The S7 fluency pulse — reserve-bank integrity, the unseen invariant,
scheduling rhythm, section scoring, and the drift report."""
import datetime
import json

import curriculum
import learner
import reader


def _state():
    return json.loads(json.dumps(learner._DEFAULT))


def _s7_state():
    s = _state()
    learner.set_placement(s, {"stage_idx": 7, "stage": "S7",
                              "stage_name": "x", "per_stage": {}})
    return s


# ── Reserve bank integrity ─────────────────────────────────────────────────────
def test_reserve_bank_is_deep_valid_and_shadowable():
    assert len(curriculum.PULSE_RESERVE) >= 4
    ids = set()
    for p in curriculum.PULSE_RESERVE:
        assert p["id"] not in ids
        ids.add(p["id"])
        assert len(p["qs"]) >= 2
        for q in p["qs"]:
            assert 0 <= q["a"] < len(q["choices"]) and len(q["choices"]) >= 2
        zh, py = p["shadow"]
        assert zh in p["zh"], f"{p['id']}: shadow line is not in the passage"
        hanzi = [c for c in zh if "㐀" <= c <= "鿿"]
        assert len(hanzi) == len(py.split()), \
            f"{p['id']}: shadow pinyin misaligned with its hanzi"
        tones = [curriculum._py_tone(s) for s in py.split()]
        assert all(1 <= t <= 5 for t in tones)
        assert sum(1 for t in tones if t in (1, 2, 3, 4)) >= 3   # scoreable


def test_reserve_passages_use_only_taught_characters():
    """The pulse is a diagnostic, not a trap — unseen TEXT, known WORDS.
    Every character must be taught by S6 (seeds + grammar examples + 成语)."""
    known = set("安娜王明")
    for s in curriculum.STAGES:
        known |= {c for w in curriculum.SEEDS.get(s["id"], []) for c in w[0]}
        known |= {c for g in curriculum.GRAMMAR if g["stage"] == s["id"]
                  for zh, _, _ in g["examples"] for c in zh if "㐀" <= c <= "鿿"}
    known |= {c for cy in curriculum.CHENGYU for c in cy["zh"]}
    for p in curriculum.PULSE_RESERVE:
        unk = {c for c in p["zh"] if "㐀" <= c <= "鿿" and c not in known}
        assert not unk, f"{p['id']} uses untaught characters: {''.join(sorted(unk))}"


def test_reserve_passages_never_appear_in_the_reader():
    """Unseen is the point: the reserve bank must stay out of the reader and
    out of the practice banks, or the pulse measures memory, not fluency."""
    reader_text = "".join(tok["z"] for t in reader.TEXTS
                          for s in t["sentences"] for tok in s["t"])
    bank_text = "".join(p["zh"] for bank in (curriculum.READING,
                                             curriculum.LISTENING_PASSAGES)
                        for ps in bank.values() for p in ps)
    for p in curriculum.PULSE_RESERVE:
        probe = p["zh"][:20]
        assert probe not in reader_text, f"{p['id']} leaks into the reader"
        assert probe not in bank_text, f"{p['id']} leaks into a practice bank"


# ── The deal ───────────────────────────────────────────────────────────────────
def test_deal_is_deterministic_and_never_reads_what_it_plays():
    d0a, d0b = curriculum.pulse_deal(0), curriculum.pulse_deal(0)
    assert d0a == d0b
    for n in range(8):
        d = curriculum.pulse_deal(n)
        assert d["reading"]["id"] != d["listening"]["id"]
        assert all("a" not in q for q in d["reading"]["qs"])     # server-scored
        assert d["compose"]["id"].startswith("S7-")
        assert len(d["shadow"]["tones"]) == len(d["shadow"]["py"].split())
    # rotation actually moves through the bank
    assert curriculum.pulse_deal(0)["reading"]["id"] != \
        curriculum.pulse_deal(1)["reading"]["id"]


def test_s7_composition_prompts_require_a_chengyu():
    for pr in curriculum.COMPOSITION_PROMPTS["S7"]:
        assert pr.get("require_chengyu"), f"{pr['id']} lets the 成语 slide"
    # and the S7 daily compose no longer falls back to S2 prompts
    d = datetime.date(2026, 7, 10)
    assert curriculum.composition_prompt_of_the_day("S7", d)["id"].startswith("S7-")


def test_score_pulse_passage_counts_rights():
    p = curriculum.PULSE_RESERVE[0]
    full = {f"{p['id']}-q{i}": q["a"] for i, q in enumerate(p["qs"])}
    r = curriculum.score_pulse_passage(p["id"], full)
    assert r["right"] == r["total"] == len(p["qs"])
    assert curriculum.score_pulse_passage(p["id"], {})["right"] == 0


# ── Scheduling: the every-two-weeks rhythm ─────────────────────────────────────
def test_pulse_is_due_at_s7_and_only_at_s7():
    assert learner.pulse_due(_state()) is False        # S0: no pulse
    s = _s7_state()
    assert learner.pulse_due(s) is True                # arrival at S7: due
    assert learner.recommend(s)["id"] == "pulse"       # and recommended


def test_pulse_rhythm_waits_out_the_interval():
    s = _s7_state()
    learner.pulse_start(s)
    _finish_pulse(s)
    assert learner.pulse_due(s) is False               # just done: not due
    assert learner.recommend(s)["id"] != "pulse"
    s["pulse"][-1]["date"] = (
        datetime.date.today()
        - datetime.timedelta(days=curriculum.PULSE_INTERVAL_DAYS)).isoformat()
    assert learner.pulse_due(s) is True                # a fortnight later: due


# ── Section recording and the drift report ─────────────────────────────────────
def _finish_pulse(s, reading=(3, 3), listening=(3, 3), passed=True,
                  shadow=(8, 10)):
    learner.pulse_record(s, "reading",
                         {"id": "x", "right": reading[0], "total": reading[1]})
    learner.pulse_record(s, "listening",
                         {"id": "y", "right": listening[0], "total": listening[1]})
    learner.pulse_record(s, "compose", {"id": "z", "passed": passed})
    return learner.pulse_record(s, "shadow",
                                {"hits": shadow[0], "total": shadow[1], "pace": 1.2})


def test_pulse_report_verdicts_and_remediation():
    s = _s7_state()
    learner.pulse_start(s)
    assert s["pulse_open"] and s["pulse_open"]["n"] == 0
    report = _finish_pulse(s, reading=(3, 3), listening=(1, 3),
                           passed=False, shadow=(2, 10))
    assert report is not None and s["pulse_open"] is None
    assert report["reading"]["verdict"] == "holds"
    assert report["listening"]["verdict"] == "decayed"
    assert report["compose"]["verdict"] == "slipping"
    assert report["shadow"]["verdict"] == "decayed"
    assert report["holds"] == 1
    remedy_ids = [m["id"] for m in report["remedy"]]
    assert remedy_ids == ["listening", "compose", "tone_drill"]
    assert s["pulse"][-1] == report                    # history keeps it
    assert s["activity"][-1]["kind"] == "pulse"        # and the log saw it


def test_pulse_partial_sections_do_not_close_it():
    s = _s7_state()
    learner.pulse_start(s)
    assert learner.pulse_record(s, "reading",
                                {"id": "x", "right": 3, "total": 3}) is None
    assert s["pulse_open"] is not None and not s["pulse"]


def test_pulse_shadow_can_be_skipped_without_penalty():
    s = _s7_state()
    learner.pulse_start(s)
    learner.pulse_record(s, "reading", {"id": "x", "right": 3, "total": 3})
    learner.pulse_record(s, "listening", {"id": "y", "right": 3, "total": 3})
    learner.pulse_record(s, "compose", {"id": "z", "passed": True})
    report = learner.pulse_record(s, "shadow", {"skipped": True})
    assert report["shadow"]["verdict"] == "skipped"
    assert not report["remedy"]                        # skipped isn't a slip
    assert report["holds"] == 3


def test_pulse_view_feeds_the_progress_card():
    s = _s7_state()
    v = learner.pulse_view(s)
    assert v["at_stage"] and v["due"] and v["days_since"] is None
    learner.pulse_start(s)
    _finish_pulse(s)
    v = learner.pulse_view(s)
    assert v["due"] is False and v["days_since"] == 0
    assert v["history"] and v["history"][0]["holds"] == 4
