"""users.py — accounts, hashing, bootstrap migration, per-user learner paths."""
import json

import learner
import users


def _tmp_users(tmp_path, monkeypatch):
    monkeypatch.setattr(users, "DATA", tmp_path)
    monkeypatch.setattr(users, "USERS_FILE", tmp_path / "users.json")
    users._cache["mtime"] = None
    users._cache["data"] = {}


def test_add_verify_and_reject(tmp_path, monkeypatch):
    _tmp_users(tmp_path, monkeypatch)
    users.add("arah91", "secret-pass", "Phil")
    assert users.verify("arah91", "secret-pass")
    assert users.verify("ARAH91 ", "secret-pass")      # case/space tolerant lookup
    assert not users.verify("arah91", "wrong")
    assert not users.verify("nobody", "secret-pass")
    assert users.display_name("arah91") == "Phil"
    assert users.display_name("nobody") == "the learner"
    assert (tmp_path / "users" / "arah91").is_dir()


def test_username_and_password_rules(tmp_path, monkeypatch):
    _tmp_users(tmp_path, monkeypatch)
    for bad in ("A B", "x", "has:colon", "Иван", "a" * 31):
        try:
            users.add(bad, "longenough")
            raise AssertionError(f"{bad!r} accepted")
        except ValueError:
            pass
    try:
        users.add("ok-name", "short")
        raise AssertionError("short password accepted")
    except ValueError:
        pass


def test_salts_differ_and_passwd_rotates(tmp_path, monkeypatch):
    _tmp_users(tmp_path, monkeypatch)
    users.add("aa", "password1")
    users.add("bb", "password1")
    d = users.load_users()
    assert d["aa"]["pw"] != d["bb"]["pw"]              # per-user salt
    old = d["aa"]["pw"]
    users.set_password("aa", "password2")
    assert users.verify("aa", "password2") and not users.verify("aa", "password1")
    assert users.load_users()["aa"]["pw"] != old


def test_bootstrap_adopts_legacy_data(tmp_path, monkeypatch):
    _tmp_users(tmp_path, monkeypatch)
    (tmp_path / "state.json").write_text(json.dumps({"vocab": [1, 2, 3]}))
    (tmp_path / "conversation.json").write_text("[]")
    monkeypatch.setenv("TUTOR_PASSWORD", "boot-pass")
    monkeypatch.setenv("TUTOR_USER", "arah91")
    monkeypatch.setenv("TUTOR_USER_NAME", "Phil")
    out = users.bootstrap()
    assert out["user"] == "arah91"
    assert sorted(out["adopted"]) == ["conversation.json", "state.json"]
    assert users.verify("arah91", "boot-pass")
    assert not (tmp_path / "state.json").exists()
    moved = json.loads((tmp_path / "users" / "arah91" / "state.json").read_text())
    assert moved["vocab"] == [1, 2, 3]
    assert users.bootstrap() is None                   # never runs twice


def test_learner_paths_follow_user(monkeypatch):
    tok = learner._USER.set(None)
    try:
        assert learner.user_dir() == learner.DATA      # legacy root for scripts/tests
        learner.set_user("arah91")
        assert learner.user_dir() == learner.DATA / "users" / "arah91"
        assert learner._state_file().name == "state.json"
    finally:
        learner._USER.reset(tok)
