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


def test_reader_level_counts_cover_phase2_depth():
    counts = {lv["id"]: 0 for lv in reader.LEVELS}
    for t in reader.TEXTS:
        counts[t["level"]] += 1
    assert counts["R0"] >= 8
    assert counts["R1"] >= 8
    assert counts["R2"] >= 10
    assert counts["R3"] >= 10
    assert counts["R4"] >= 8
    assert counts["R5"] >= 6
    assert counts["R6"] >= 4
    assert counts["R7"] >= 2


def test_every_word_token_carries_pinyin_and_gloss():
    for t in reader.TEXTS:
        for s in t["sentences"]:
            for tok in s["t"]:
                if tok["p"] or tok["e"]:              # a word token
                    assert tok["p"] and tok["e"], f"{t['id']}: {tok}"
                else:                                 # bare punctuation only
                    assert len(tok["z"]) <= 2 and not tok["z"].isalnum()


NAMES = {"安娜", "王明"}                    # recognized on sight, glossed inline


def test_no_gaps_every_word_is_taught_before_use():
    """The reader is a learner's ENTIRE reading input — a text may only use
    words that this or an earlier text taught, or (the cumulative-knowledge
    rule from the pedagogy shelf) compounds whose every character is already
    known, like 二月 after 二 and 月."""
    taught_words, taught_chars = set(), set()
    for t in reader.TEXTS:
        new = {w[0] for w in t["new_words"]}
        new_chars = {c for w in new for c in w}
        for s in t["sentences"]:
            for tok in s["t"]:
                if not tok["p"]:
                    continue
                z = tok["z"]
                ok = (z in taught_words or z in new or z in NAMES
                      or all(c in taught_chars or c in new_chars for c in z))
                assert ok, f"{t['id']} uses {z} before it is taught"
        taught_words |= new
        taught_chars |= new_chars


def test_early_words_recur_in_later_texts():
    """循环练习 — recycling. Every R0/R1 word should be met again in a later
    text (the SRS deck re-drills them regardless, but recurrence in real text
    is what cements reading)."""
    early = [(t["id"], w[0]) for t in reader.TEXTS if t["level"] in ("R0", "R1")
             for w in t["new_words"]]
    order = [t["id"] for t in reader.TEXTS]
    for tid, hz in early:
        later = reader.TEXTS[order.index(tid) + 1:]
        assert any(tok["z"] == hz or (len(hz) == 1 and hz in tok["z"])
                   for t in later for s in t["sentences"] for tok in s["t"]), \
            f"{hz} (taught in {tid}) never recurs"


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


# ── Shadowing ──────────────────────────────────────────────────────────────────
def test_sentence_tones_derive_from_token_pinyin():
    t = reader.get_text("r0-1")
    tones = reader.sentence_tones(t["sentences"][0]["t"])
    assert tones == [1]                              # 一 yī
    t2 = reader.get_text("r2-2")                     # 我要喝茶。
    assert reader.sentence_tones(t2["sentences"][0]["t"]) == [3, 4, 1, 2]


def test_shadow_sentences_prefer_completed_texts():
    s = _state()
    assert reader.shadow_sentences(s, 0) == []       # S0: nothing sentence-length yet
    out = reader.shadow_sentences(s, 2)              # open-level fallback has sentences
    assert out and all(len(i["tones"]) >= 3 for i in out)
    s["reader"]["r5-1"] = {"date": "x", "score": "3/3"}
    out2 = reader.shadow_sentences(s, 5)
    assert out2 and all(i["id"].startswith("r5-1") for i in out2)
