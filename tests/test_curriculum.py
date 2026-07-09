"""curriculum.py + the learner systems built on it — placement, unlocks,
recommendations, practice generators, ingestion filename parsing."""
import json

import curriculum
import ingest
import learner


def _state():
    return json.loads(json.dumps(learner._DEFAULT))


def _tone_from_pinyin(syllable):
    marks = {
        "ā": 1, "ē": 1, "ī": 1, "ō": 1, "ū": 1, "ǖ": 1,
        "á": 2, "é": 2, "í": 2, "ó": 2, "ú": 2, "ǘ": 2,
        "ǎ": 3, "ě": 3, "ǐ": 3, "ǒ": 3, "ǔ": 3, "ǚ": 3,
        "à": 4, "è": 4, "ì": 4, "ò": 4, "ù": 4, "ǜ": 4,
    }
    for ch in syllable.lower():
        if ch in marks:
            return marks[ch]
    return 5


def _known_chars_through(stage_id):
    order = [s["id"] for s in curriculum.STAGES]
    known = set()
    for sid in order[: order.index(stage_id) + 1]:
        known |= {c for w in curriculum.SEEDS.get(sid, []) for c in w[0]}
    return known


# ── Data integrity ─────────────────────────────────────────────────────────────
def test_stage_thresholds_ascend_and_ids_are_consistent():
    ths = [s["threshold"] for s in curriculum.STAGES]
    assert ths == sorted(ths) and ths[0] == 0
    assert [s["idx"] for s in curriculum.STAGES] == list(range(len(curriculum.STAGES)))


def test_grammar_points_reference_real_stages_and_have_examples():
    ids = {s["id"] for s in curriculum.STAGES}
    seen = set()
    for g in curriculum.GRAMMAR:
        assert g["stage"] in ids
        assert g["id"] not in seen
        seen.add(g["id"])
        assert g["examples"] and all(len(e) == 3 for e in g["examples"])
        assert len(g["explain"]) > 40


def test_seed_tones_line_up_with_pinyin_syllables():
    for sid, words in curriculum.SEEDS.items():
        for hz, py, en, tones in words:
            assert len(py.split()) == len(tones), f"{sid} {hz}"
            assert all(1 <= t <= 5 for t in tones)
            derived = [_tone_from_pinyin(s) for s in py.split()]
            assert derived == tones, f"{sid} {hz}: {py} marks {derived}, tones {tones}"


def test_seed_words_are_unique_across_stages():
    seen = {}
    for sid, words in curriculum.SEEDS.items():
        for hz, *_ in words:
            assert hz not in seen, f"{hz} appears in both {seen[hz]} and {sid}"
            seen[hz] = sid


def test_reading_passages_have_valid_answer_indices():
    for sid, passages in curriculum.READING.items():
        for p in passages:
            for q in p["qs"]:
                assert 0 <= q["a"] < len(q["choices"])


def test_beginner_arc_never_runs_out_of_material():
    """Can't be stuck between levels: the deterministic content available by
    the end of stage k (cumulative seeds + reader words) must cover the entry
    threshold of stage k+1. Phase 2 extends this through leaving S4 — move the
    cutoff up, never down."""
    import reader
    covered_through = "S4"
    vocab = set()
    for k, s in enumerate(curriculum.STAGES[:-1]):
        vocab |= {w[0] for w in curriculum.SEEDS.get(s["id"], [])}
        vocab |= {w[0] for t in reader.TEXTS
                  if reader._LEVEL_IDX[t["level"]] <= k for w in t["new_words"]}
        need = curriculum.STAGES[k + 1]["threshold"]
        assert len(vocab) >= need, \
            f"stuck leaving {s['id']}: {len(vocab)} words available, {need} needed"
        if s["id"] == covered_through:
            break


def test_writing_ladder_is_sound_through_w2():
    fixed = [r for r in curriculum.WRITING_RUNGS if r["id"] in ("W0", "W1", "W2")]
    counts = {r["id"]: len(r["chars"]) for r in fixed}
    assert counts["W0"] >= 17
    assert counts["W1"] >= 16
    assert counts["W2"] >= 30
    seen = set()
    seed_words = {w[0] for words in curriculum.SEEDS.values() for w in words}
    for rung in fixed:
        for hz, py, en in rung["chars"]:
            assert len(hz) == 1 and "㐀" <= hz <= "鿿"
            assert hz not in seen, f"{hz} appears in multiple writing rungs"
            assert hz in seed_words, f"{hz} is writable but not a seed word"
            assert py and en
            seen.add(hz)


def test_grammar_phase1_has_depth_and_covered_examples():
    phase1 = [g for g in curriculum.GRAMMAR if g["stage"] in ("S1", "S2", "S3")]
    assert len(phase1) >= 45
    names = set("安娜王明")
    for g in phase1:
        known = _known_chars_through(g["stage"]) | names
        for zh, _, _ in g["examples"]:
            unk = {c for c in zh if "㐀" <= c <= "鿿" and c not in known}
            assert not unk, f"{g['id']} uses untaught characters: {''.join(sorted(unk))}"


def test_reading_passages_use_only_characters_taught_by_their_stage():
    """No gaps: a practice passage may only use characters a learner at that
    stage has met — cumulative seed words plus unlocked grammar examples.
    Proper names are the one exception (recognized, not learned)."""
    names = "安娜王明"
    order = [s["id"] for s in curriculum.STAGES]
    known = set()
    known_at = {}
    for sid in order:
        known |= {c for w in curriculum.SEEDS.get(sid, []) for c in w[0]}
        known |= {c for g in curriculum.GRAMMAR if g["stage"] == sid
                  for zh, _, _ in g["examples"] for c in zh if "㐀" <= c <= "鿿"}
        known_at[sid] = set(known)
    for sid, passages in curriculum.READING.items():
        for i, p in enumerate(passages):
            unk = {c for c in p["zh"]
                   if "㐀" <= c <= "鿿" and c not in known_at[sid] and c not in names}
            assert not unk, f"{sid} passage {i} uses untaught characters: {''.join(unk)}"


# ── Placement ──────────────────────────────────────────────────────────────────
def test_placement_is_deterministic_and_scored_server_side():
    a, b = curriculum.placement_items(), curriculum.placement_items()
    assert a == b and len(a) == 4 * len(curriculum.PLACEMENT_STAGES)
    assert all("answer" not in it for it in curriculum.placement_public())


def test_placement_scoring_perfect_blank_and_gap():
    items = curriculum.placement_items()
    full = {it["id"]: it["answer"] for it in items}
    assert curriculum.score_placement(full)["stage"] == "S6"
    assert curriculum.score_placement({})["stage"] == "S0"
    # a gap at S4 caps placement at S3 even with S5 passed (contiguous rule)
    part = {it["id"]: it["answer"] for it in items
            if it["stage"] in ("S1", "S2", "S3", "S5")}
    assert curriculum.score_placement(part)["stage"] == "S3"


def test_can_do_checks_are_server_scored_and_targeted():
    for sid in curriculum.CAN_DO_STAGES:
        public = curriculum.can_do_public(sid)
        private = curriculum.can_do_items(sid)
        assert public and len(public) == len(private)
        assert all("answer" not in it and "remediate" not in it for it in public)
        assert all(it["kind"] in ("reading", "listening") for it in private)
        assert any(it.get("critical") for it in private)
    items = curriculum.can_do_items("S2")
    full = {it["id"]: it["answer"] for it in items}
    result = curriculum.score_can_do("S2", full)
    assert result["passed"] is True and result["lift_stage"] == "S3"
    critical = next(it for it in items if it["critical"])
    miss = {**full, critical["id"]: (critical["answer"] + 1) % len(critical["choices"])}
    result = curriculum.score_can_do("S2", miss)
    assert result["passed"] is False
    assert result["critical_missed"] == 1
    assert result["remediation"] and result["missed"][0]["skill"]


# ── Grammar unlocks ────────────────────────────────────────────────────────────
def test_grammar_unlocks_follow_stage():
    at_s0 = curriculum.grammar_for(0)
    assert not any(g["unlocked"] for g in at_s0)
    at_s3 = {g["id"]: g["unlocked"] for g in curriculum.grammar_for(3)}
    assert at_s3["le-completed"] and not at_s3["bei-passive"]


# ── Practice generators ────────────────────────────────────────────────────────
def test_reading_practice_s0_is_pinyin_only_tone_recognition():
    out = curriculum.reading_practice([], "S0")
    assert out["items"] and all(i["kind"] == "tone" and i["zh"] is None
                                for i in out["items"])


def test_practice_items_have_valid_answers_and_audio_text():
    for sid in ("S1", "S3", "S6"):
        r = curriculum.reading_practice([], sid)
        li = curriculum.listening_practice([], sid)
        for it in r["items"] + li["items"]:
            assert 0 <= it["a"] < len(it["choices"])
        assert all(it["zh"] for it in li["items"])   # listening always speaks


def test_practice_prefers_learner_vocab():
    vocab = [{"hanzi": "猫", "pinyin": "māo", "english": "cat", "tones": [1]}]
    out = curriculum.listening_practice(vocab, "S0", n=40)
    assert any(it["zh"] == "猫" for it in out["items"])


def test_dictation_normalizes_punctuation_and_accepts_alternates():
    public = curriculum.dictation_public("S3")
    assert public and all("answers" not in it for it in public)
    assert curriculum.normalize_dictation_answer(" 往左走，再往右走。 ") == "往左走再往右走"
    items = curriculum.dictation_items("S3")
    full = {it["id"]: it["answers"][0] for it in items}
    result = curriculum.score_dictation("S3", full)
    assert result["passed"] is True
    alt = dict(full)
    alt["S3-dict-directions"] = "往左走，然后往右走。"
    assert curriculum.score_dictation("S3", alt)["passed"] is True
    alt["S3-dict-work"] = "今天我工作了"
    result = curriculum.score_dictation("S3", alt)
    assert result["passed"] is False
    assert result["remediation"][0]["label"]


# ── Learner: stage, settings, recommendations ──────────────────────────────────
def _learn_words(s, n):
    for i in range(n):
        hz = f"字{i}"
        learner.add_word(s, hz, "zì", f"word {i}", [4])
        w = s["vocab"][-1]
        w["reps"], w["interval"] = 2, 3              # "learned" by definition
        w["due"] = "2999-01-01"


def test_speaking_stage_derives_from_learned_words_and_placement_lifts():
    s = _state()
    assert learner.speaking_stage(s) == 0
    _learn_words(s, 8)
    assert learner.speaking_stage(s) == 1
    learner.set_placement(s, {"stage_idx": 3, "stage": "S3",
                              "stage_name": "x", "per_stage": {}})
    assert learner.speaking_stage(s) == 3            # placement lifts
    _learn_words(s, 300)
    assert learner.speaking_stage(s) == 3            # 308 learned -> S3 either way
    learner.set_can_do(s, {"stage": "S3", "passed": True,
                           "lift_stage_idx": 4, "lift_stage": "S4"})
    assert learner.speaking_stage(s) == 4            # can-do lifts separately
    assert s["placement"]["stage_idx"] == 3


def test_settings_update_validates_keys_and_values():
    s = _state()
    out = learner.update_settings(s, {"immersion": 1, "tone_display": "numbers",
                                      "bogus": True, "show_pinyin": False})
    assert out["immersion"] is True and out["tone_display"] == "numbers"
    assert out["show_pinyin"] is False and "bogus" not in out
    learner.update_settings(s, {"tone_display": "junk"})
    assert s["settings"]["tone_display"] == "marks"  # bad value falls back


def test_recommend_cascade():
    import reader
    s = _state()
    assert learner.recommend(s)["id"] == "placement"     # brand new learner
    learner.set_placement(s, {"stage_idx": 0, "stage": "S0",
                              "stage_name": "x", "per_stage": {}})
    learner.add_word(s, "妈", "mā", "mom", [1])
    assert learner.recommend(s)["id"] == "review"        # due word outranks all
    learner.grade_word(s, "妈", 5)
    assert learner.recommend(s)["id"] == "read"          # graded reader first
    s["reader"] = {t["id"]: {"date": "2000-01-01", "score": "1/1"}
                   for t in reader.TEXTS}                # ladder finished ->
    assert learner.recommend(s)["id"] == "reading"       # generic practice
    learner.record_activity(s, "reading", "S0", "4/6")
    assert learner.recommend(s)["id"] == "lesson"        # practiced -> new material
    learner.record_activity(s, "lesson")
    assert learner.recommend(s)["id"] == "writing"       # everything done -> pad
    learner.record_activity(s, "listening", "S0", "5/6")
    assert learner.recommend(s)["id"] == "writing"


def test_recommend_alternates_practice_channel():
    import reader
    s = _state()
    learner.set_placement(s, {"stage_idx": 1, "stage": "S1",
                              "stage_name": "x", "per_stage": {}})
    s["reader"] = {t["id"]: {"date": "2000-01-01", "score": "1/1"}
                   for t in reader.TEXTS}                # reader done: quiz practice
    s["activity"] = [{"date": "2000-01-01", "kind": "reading",
                      "detail": "S1", "score": "4/6"}]
    assert learner.recommend(s)["id"] == "listening"     # yesterday was reading


def test_writing_rung_walks_the_ladder():
    s = _state()
    assert learner.writing_rung(s) == "W0"
    for h, _, _ in curriculum.WRITING_RUNGS[0]["chars"]:
        learner.record_writing(s, h, 0)
    assert learner.writing_rung(s) == "W1"
    for h, _, _ in curriculum.WRITING_RUNGS[1]["chars"]:
        learner.record_writing(s, h, 1)
    assert learner.writing_rung(s) == "W2"
    for h, _, _ in curriculum.WRITING_RUNGS[2]["chars"]:
        learner.record_writing(s, h, 1)
    assert learner.writing_rung(s) == "W3"


def test_activity_log_caps():
    s = _state()
    for i in range(80):
        learner.record_activity(s, "review", str(i))
    assert len(s["activity"]) == 60


# ── Ingestion ──────────────────────────────────────────────────────────────────
def test_ingest_parse_filename():
    m = ingest.parse_filename(
        "Some Book Title -- Jane Doe -- Series, City, 2020 -- Publisher "
        "-- isbn13 9781138308398 -- Anna's Archive.pdf")
    assert m["title"] == "Some Book Title"
    assert m["authors"] == "Jane Doe"
    assert m["isbn13"] == "9781138308398"


def test_ingest_search_matches_books_and_sections():
    index = {"books": [{"title": "HSK Standard Course", "file": "f.pdf",
                        "sections": [{"title": "HSK Standard Course 3 Textbook",
                                      "page": 42, "depth": 0}]}]}
    hits = ingest.search(index, "course 3")
    assert hits and hits[0]["page"] == 42
    assert ingest.search(index, "") == []
