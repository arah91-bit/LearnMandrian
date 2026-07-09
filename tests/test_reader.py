"""reader.py — data integrity, unlocks, progression, SRS handoff."""
import json

import learner
import reader


def _state():
    return json.loads(json.dumps(learner._DEFAULT))


# ── Data integrity ─────────────────────────────────────────────────────────────
def test_ids_unique_and_levels_real():
    ids, level_ids = set(), {lv["id"] for lv in reader.LEVELS}
    for t in reader.TEXTS:
        assert t["id"] not in ids
        ids.add(t["id"])
        assert t["level"] in level_ids
    for lv in reader.LEVELS:              # no empty rungs on the ladder
        assert any(t["level"] == lv["id"] for t in reader.TEXTS)


def test_every_word_token_carries_pinyin_and_gloss():
    for t in reader.TEXTS:
        for s in t["sentences"]:
            for tok in s["t"]:
                if tok["p"] or tok["e"]:              # a word token
                    assert tok["p"] and tok["e"], f"{t['id']}: {tok}"
                else:                                 # bare punctuation only
                    assert len(tok["z"]) <= 2 and not tok["z"].isalnum()


def test_new_words_actually_appear_in_their_text():
    for t in reader.TEXTS:
        toks = {tok["z"] for s in t["sentences"] for tok in s["t"]}
        toks |= {s["who"] for s in t["sentences"] if s["who"]}   # speaker labels read too
        for hz, py, en, tones in t["new_words"]:
            assert hz in toks, f"{t['id']} teaches {hz} but never shows it"
            assert all(1 <= x <= 5 for x in tones)


def test_questions_have_valid_answers_and_a_translation_exists():
    for t in reader.TEXTS:
        assert t["qs"] and t["en"] and t["intro"]
        for q in t["qs"]:
            assert 0 <= q["a"] < len(q["choices"]) and len(q["choices"]) >= 2


# ── Unlocks & progression ──────────────────────────────────────────────────────
def test_fresh_learner_starts_at_r0_first_text():
    s = _state()
    assert reader.open_through(s, 0) == 0
    assert reader.next_text(s, 0)["id"] == "r0-1"
    v = reader.view(s, 0)
    assert v["levels"][0]["open"] and not v["levels"][1]["open"]


def test_finishing_a_level_opens_the_next():
    s = _state()
    for t in reader.TEXTS:
        if t["level"] == "R0":
            reader.complete(s, t["id"], "2/2")
    assert reader.open_through(s, 0) == 1
    assert reader.next_text(s, 0)["level"] == "R1"


def test_speaking_stage_sets_a_floor():
    s = _state()
    assert reader.open_through(s, 3) == 3           # S3 learner reads dialogues now
    v = reader.view(s, 3)
    assert v["levels"][3]["open"] and not v["levels"][4]["open"]


def test_complete_marks_done_and_returns_srs_words():
    s = _state()
    words = reader.complete(s, "r0-1", "2/2")
    assert ("一", "yī", "one", [1]) in words
    assert s["reader"]["r0-1"]["score"] == "2/2"
    assert reader.next_text(s, 0)["id"] == "r0-2"
    assert reader.complete(s, "nope", "1/1") is None


def test_recommend_points_at_the_reader():
    s = _state()
    learner.set_placement(s, {"stage_idx": 0, "stage": "S0",
                              "stage_name": "x", "per_stage": {}})
    rec = learner.recommend(s)
    assert rec["id"] == "read" and rec["tid"] == "r0-1"
    learner.record_activity(s, "read", "r0-1", "2/2")
    assert learner.recommend(s)["id"] == "lesson"   # reader done today -> new material
