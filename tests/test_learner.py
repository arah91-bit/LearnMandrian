"""learner.py — SRS scheduling, tone stats, plan, streak."""
import datetime
import json

import learner


def _state():
    return json.loads(json.dumps(learner._DEFAULT))


def test_add_and_dedupe():
    s = _state()
    assert "added" in learner.add_word(s, "妈", "mā", "mom", [1])
    assert "already" in learner.add_word(s, "妈", "mā", "mom", [1])
    assert len(s["vocab"]) == 1 and s["vocab"][0]["due"] == learner._today()


def test_srs_schedule_grows_then_resets():
    s = _state()
    learner.add_word(s, "买", "mǎi", "to buy", [3])
    learner.grade_word(s, "买", 5)
    w = s["vocab"][0]
    assert w["interval"] == 1
    learner.grade_word(s, "买", 5)
    assert w["interval"] == 3
    learner.grade_word(s, "买", 4)
    assert w["interval"] > 3 and w["reps"] == 3
    learner.grade_word(s, "买", 1)          # fail -> relearn today
    assert w["interval"] == 0 and w["reps"] == 0
    assert w["due"] == learner._today()
    assert w["ease"] >= 1.3


def test_grade_unknown_word_is_soft():
    s = _state()
    assert "not in the vocab list" in learner.grade_word(s, "猫", 5)


def test_tone_stats_and_confusions():
    s = _state()
    learner.log_tone_attempt(s, [3, 4], [2, 4])   # one miss (3->2), one hit
    learner.log_tone_attempt(s, [3], [2], hanzi="马", pinyin="mǎ",
                             audio_path="audio_debug/test.webm", source="unit")
    acc = learner.tone_accuracy(s)
    assert acc[3] == {"correct": 0, "total": 2}
    assert acc[4] == {"correct": 1, "total": 1}
    top = learner.top_confusions(s)
    assert top[0] == {"expected": 3, "heard": 2, "count": 2}
    targets = learner.tone_drill_targets(s)
    assert targets[0]["hanzi"] == "马"
    assert targets[0]["audio"].endswith("test.webm")


def test_tone_attempt_keeps_unheard_targets_for_debugging():
    s = _state()
    learner.log_tone_attempt(s, [2, 3], [], hanzi="你好", pinyin="nǐ hǎo",
                             audio_path="audio_debug/test.webm", source="unit")

    assert s["tone_stats"] == {}
    assert s["tone_attempts"][0]["expected"] == [2, 3]
    assert s["tone_attempts"][0]["heard"] == []


def test_streak_counts_back_from_today_or_yesterday():
    s = _state()
    today = datetime.date.today()
    s["days"] = [(today - datetime.timedelta(days=d)).isoformat() for d in (2, 1)]
    assert learner.streak(s) == 2            # nothing yet today: yesterday's run
    learner.touch_day(s)
    assert learner.streak(s) == 3
    s2 = _state()
    s2["days"] = [(today - datetime.timedelta(days=5)).isoformat()]
    assert learner.streak(s2) == 0            # broken streak


def test_plan_sessions_and_snapshot():
    s = _state()
    learner.update_plan(s, focus="four tones", next_up=["numbers"], notes="likes drills")
    learner.end_session(s, "learned mā and má")
    learner.add_word(s, "妈", "mā", "mom", [1])
    s["activity"].append({"date": learner._today(), "kind": "read",
                          "detail": "r1-1", "score": "2/2"})
    snap = learner.snapshot(s)
    assert "four tones" in snap and "Due for review now" in snap and "mā" in snap
    assert "Stage word-plan not yet taught" in snap
    assert "Last reader text: 你好" in snap
    view = learner.api_view(s)
    assert view["stats"]["due_count"] == 1 and view["sessions"][0]["summary"]


def test_snapshot_deals_a_theme_at_s4_plus():
    s = _state()
    learner.set_placement(s, {"stage_idx": 5, "stage": "S5",
                              "stage_name": "x", "per_stage": {}})
    assert "Conversation theme of the day" in learner.snapshot(s)
    s2 = _state()
    assert "Conversation theme" not in learner.snapshot(s2)   # beginners drill, not chat
