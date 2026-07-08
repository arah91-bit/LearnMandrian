"""curriculum.py + the learner systems built on it — placement, unlocks,
recommendations, practice generators, ingestion filename parsing."""
import json

import curriculum
import ingest
import learner


def _state():
    return json.loads(json.dumps(learner._DEFAULT))


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


def test_reading_passages_have_valid_answer_indices():
    for sid, passages in curriculum.READING.items():
        for p in passages:
            for q in p["qs"]:
                assert 0 <= q["a"] < len(q["choices"])


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


def test_settings_update_validates_keys_and_values():
    s = _state()
    out = learner.update_settings(s, {"immersion": 1, "tone_display": "numbers",
                                      "bogus": True, "show_pinyin": False})
    assert out["immersion"] is True and out["tone_display"] == "numbers"
    assert out["show_pinyin"] is False and "bogus" not in out
    learner.update_settings(s, {"tone_display": "junk"})
    assert s["settings"]["tone_display"] == "marks"  # bad value falls back


def test_recommend_cascade():
    s = _state()
    assert learner.recommend(s)["id"] == "placement"     # brand new learner
    learner.set_placement(s, {"stage_idx": 0, "stage": "S0",
                              "stage_name": "x", "per_stage": {}})
    learner.add_word(s, "妈", "mā", "mom", [1])
    assert learner.recommend(s)["id"] == "review"        # due word outranks all
    learner.grade_word(s, "妈", 5)
    assert learner.recommend(s)["id"] == "reading"       # first practice today
    learner.record_activity(s, "reading", "S0", "4/6")
    assert learner.recommend(s)["id"] == "lesson"        # practiced -> new material
    learner.record_activity(s, "lesson")
    assert learner.recommend(s)["id"] == "writing"       # everything done -> pad
    learner.record_activity(s, "listening", "S0", "5/6")
    assert learner.recommend(s)["id"] == "writing"


def test_recommend_alternates_practice_channel():
    s = _state()
    learner.set_placement(s, {"stage_idx": 1, "stage": "S1",
                              "stage_name": "x", "per_stage": {}})
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
