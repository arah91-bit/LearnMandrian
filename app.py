"""LanguageTutor — voice-first Mandarin tutor.

Architecture (the whole point, see spike/RESULTS.md): NO voice-to-voice model.
- ears  = gpt-4o-transcribe (STT, pay-per-second)
- brain = claude-sonnet-5 (text — where the actual tutoring intelligence lives)
- mouth = gpt-4o-mini-tts (pay-per-character)
- tone ear = tone_ear.py, local DSP, free — the thing audio LLMs can't do (40%
  vs our 93%, real speakers); its report is injected into the brain's context
  each turn.

Single-user app behind an auth cookie (LifeLog pattern): every path except
/healthz and /auth/login requires the session cookie; bare paths get the login
page, /api/* gets 401. Deploy notes in DEPLOY.md-to-be; test instance is
testlanguagetutor.arahub.org (compose service languagetutor-test).
"""
import hashlib
import hmac
import json
import logging
import os
import pathlib
import re
import subprocess
import tempfile
import time
from urllib.parse import quote

import anthropic
import httpx
import openai
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

import curriculum
import ingest
import learner
from api_alerts import page_if_billing
from tone_ear import ToneEar

log = logging.getLogger("tutor")
logging.basicConfig(level=logging.INFO)

HERE = pathlib.Path(__file__).parent
DATA = pathlib.Path(os.environ.get("DATA_DIR", HERE / "data"))
DATA.mkdir(parents=True, exist_ok=True)
CONVO = DATA / "conversation.json"

SECRET = os.environ["TUTOR_SESSION_SECRET"]
PASSWORD = os.environ["TUTOR_PASSWORD"]

BRAIN_MODEL = "claude-sonnet-5"
STT_MODEL = "gpt-4o-transcribe"
ZH_TTS_MODEL = "gpt-4o-mini-tts"
ZH_TTS_VOICE = "nova"
ZH_TTS_STYLE = ("A native Mandarin teacher modeling pronunciation for a beginner. "
                "Clear standard Beijing Mandarin, learner-friendly pace, exact "
                "lexical tones.")
# English rides the self-hosted Kokoro voice Phil already picked for LifeLog
# (af_heart via the shared `voice` container); hanzi runs can't go through it
# (English-only phonemizer), so they're synthesized by the Mandarin-capable
# OpenAI voice and the segments are stitched. Heart carries most of the airtime.
VOICE_URL = os.environ.get("VOICE_URL", "http://voice:8001").rstrip("/")
HEART_VOICE = "k-heart"
MAX_MESSAGES = 40        # conversation window kept on disk / sent to the brain

SYSTEM = (HERE / "tutor_prompt.md").read_text() + "\n\n" + (HERE / "curriculum.md").read_text()
EAR = ToneEar()
_oai = openai.OpenAI()
_claude = anthropic.Anthropic()


def _cookie_value():
    return hmac.new(SECRET.encode(), b"tutor-v1", hashlib.sha256).hexdigest()


_PUBLIC = ("/healthz", "/auth/login",
           # PWA install assets: the browser fetches manifest icons without
           # credentials, so these must not bounce to the login page
           "/manifest.json", "/icon-192.png", "/icon-512.png", "/sw.js")


class Auth(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if (path in _PUBLIC
                or hmac.compare_digest(request.cookies.get("lt_session", ""),
                                       _cookie_value())):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"error": "not authenticated"}, status_code=401)
        return HTMLResponse(LOGIN_HTML, status_code=401)


app = FastAPI()
app.add_middleware(Auth)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


@app.get("/healthz")
async def healthz():
    return {"ok": True}


# Login throttle: the URL is on the open internet behind Caddy. Global, not
# per-IP (single user; a distributed guesser defeats per-IP anyway) — after
# _LOGIN_MAX failures in the window, everyone waits. Phil's cookie lasts 90
# days, so a lockout costs him nothing.
_login_fails, _LOGIN_MAX, _LOGIN_WINDOW = [], 10, 900


@app.post("/auth/login")
async def login(request: Request):
    form = await request.form()
    now = time.time()
    _login_fails[:] = [t for t in _login_fails if now - t < _LOGIN_WINDOW]
    if len(_login_fails) >= _LOGIN_MAX:
        return HTMLResponse(LOGIN_HTML.replace("<!--err-->",
                            "<p class=err>Too many attempts — try again later.</p>"),
                            status_code=429)
    if not hmac.compare_digest(str(form.get("password", "")), PASSWORD):
        _login_fails.append(now)
        return HTMLResponse(LOGIN_HTML.replace("<!--err-->",
                            "<p class=err>Wrong password.</p>"), status_code=401)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("lt_session", _cookie_value(), max_age=90 * 86400,
                    httponly=True, secure=True, samesite="lax")
    return resp


@app.get("/")
async def index():
    return FileResponse(HERE / "static" / "index.html")


@app.get("/manifest.json")
async def manifest():
    return FileResponse(HERE / "static" / "manifest.json")


@app.get("/icon-192.png")
async def icon192():
    return FileResponse(HERE / "static" / "icon-192.png")


@app.get("/icon-512.png")
async def icon512():
    return FileResponse(HERE / "static" / "icon-512.png")


@app.get("/sw.js")
async def sw():
    """Stamp the shell's mtime into the worker so every deploy byte-changes it —
    that's what makes stale home-screen installs reload themselves (see sw.js)."""
    js = (HERE / "static" / "sw.js").read_text()
    stamp = int((HERE / "static" / "index.html").stat().st_mtime)
    return Response(content=js + f"\n// build {stamp}\n",
                    media_type="application/javascript")


def _load_convo():
    return json.loads(CONVO.read_text()) if CONVO.exists() else []


def _save_convo(msgs):
    tmp = CONVO.with_suffix(".tmp")
    tmp.write_text(json.dumps(msgs[-MAX_MESSAGES:], ensure_ascii=False, indent=1))
    tmp.replace(CONVO)


def _webm_to_wav(blob):
    """Browser audio (webm/opus, mp4, whatever) -> 16k mono wav via ffmpeg."""
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(blob)
        src = f.name
    dst = src + ".wav"
    r = subprocess.run(["ffmpeg", "-y", "-i", src, "-ar", "16000", "-ac", "1", dst],
                       capture_output=True, timeout=30)
    os.unlink(src)
    if r.returncode != 0:
        raise HTTPException(400, "could not decode audio: "
                            + r.stderr.decode()[-200:])
    return dst


def _stt_local(wav):
    """Fallback ears: the self-hosted Whisper in the shared voice container.
    Weaker on mixed EN/zh beginner speech than gpt-4o-transcribe, but it keeps
    lessons running through an OpenAI outage or a dead key."""
    with open(wav, "rb") as f:
        r = httpx.post(f"{VOICE_URL}/transcribe",
                       files={"file": ("turn.wav", f, "audio/wav")}, timeout=120)
    r.raise_for_status()
    return " ".join(s["text"].strip() for s in r.json().get("segments", [])).strip()


def _stt(wav):
    try:
        with open(wav, "rb") as f:
            tr = _oai.audio.transcriptions.create(
                model=STT_MODEL, file=f,
                prompt="A beginner Mandarin lesson. The speaker mixes English "
                       "and Mandarin Chinese, sometimes single syllables like ma or tang.")
        return tr.text.strip()
    except Exception as e:
        page_if_billing("openai", e)
        log.warning("openai stt failed — falling back to local whisper: %s", str(e)[:150])
        try:
            return _stt_local(wav)
        except Exception as e2:
            raise HTTPException(502, f"speech-to-text failed: {str(e2)[:200]}")


# ── Brain tools: how the tutor maintains the learner state it teaches from ────
TOOLS = [
    {"name": "add_word",
     "description": "Add a newly introduced word to the vocabulary tracker with "
                    "spaced-repetition scheduling. Call the moment you teach a new word.",
     "input_schema": {"type": "object", "properties": {
         "hanzi": {"type": "string"},
         "pinyin": {"type": "string", "description": "with tone marks, e.g. mǎi"},
         "english": {"type": "string"},
         "tones": {"type": "array", "items": {"type": "integer"},
                   "description": "tone number per syllable, 1-4 (5 = neutral)"}},
         "required": ["hanzi", "pinyin", "english", "tones"]}},
    {"name": "grade_word",
     "description": "Record how a review/practice of a known word went; reschedules it. "
                    "5 effortless, 4 solid, 3 shaky pass, 2 close miss, 0-1 fail.",
     "input_schema": {"type": "object", "properties": {
         "hanzi": {"type": "string"}, "grade": {"type": "integer"}},
         "required": ["hanzi", "grade"]}},
    {"name": "log_tone_attempt",
     "description": "Record a spoken tone attempt when you know what tones Phil was "
                    "aiming for: expected tones vs what the tone-ear heard. Feeds the "
                    "tone accuracy stats he sees on his Progress screen.",
     "input_schema": {"type": "object", "properties": {
         "expected": {"type": "array", "items": {"type": "integer"}},
         "heard": {"type": "array", "items": {"type": "integer"}}},
         "required": ["expected", "heard"]}},
    {"name": "update_plan",
     "description": "Keep the visible lesson plan current: today's focus, what's coming "
                    "next (short phrases), and brief notes-to-self. Phil sees this on his "
                    "Plan screen — keep it in plain learner-facing language.",
     "input_schema": {"type": "object", "properties": {
         "focus": {"type": "string"},
         "next_up": {"type": "array", "items": {"type": "string"}},
         "notes": {"type": "string"}}, "required": []}},
    {"name": "end_session",
     "description": "When a session wraps up, record a one-sentence summary of what was "
                    "covered and how it went. Shows in his session history.",
     "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}},
         "required": ["summary"]}},
]


def _run_tool(state, name, args):
    try:
        if name == "add_word":
            return learner.add_word(state, args["hanzi"], args["pinyin"],
                                    args["english"], args["tones"])
        if name == "grade_word":
            return learner.grade_word(state, args["hanzi"], args["grade"])
        if name == "log_tone_attempt":
            return learner.log_tone_attempt(state, args["expected"], args["heard"])
        if name == "update_plan":
            return learner.update_plan(state, args.get("focus"),
                                       args.get("next_up"), args.get("notes"))
        if name == "end_session":
            return learner.end_session(state, args["summary"])
        return f"unknown tool {name}"
    except Exception as e:                    # bad args must not kill the turn
        return f"tool error: {e}"


# Which model runs the lessons. The tutor is an instructor working a fixed
# curriculum with tools — a job a cheaper model handles well (and this app must
# run itself for years, so cost matters): deepseek is ~1/30th of Sonnet per
# turn, gpt-mini sits in between. BRAIN_PROVIDER picks the primary; on ANY
# provider failure the turn falls through the rest of BRAIN_CHAIN (billing
# failures also page via api_alerts), so one dead key never stops a lesson.
# deepseek-chat is deprecated 2026-07-24 → default to its successor id
# explicitly so the app doesn't sit on a dying alias.
BRAIN_PROVIDER = os.environ.get("BRAIN_PROVIDER", "claude")   # claude | deepseek | gpt
BRAIN_CHAIN = ["deepseek", "gpt", "claude"]
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
GPT_MODEL = os.environ.get("GPT_MODEL", "gpt-5.4-mini-2026-03-17")
_deepseek = None


def _ds():
    global _deepseek
    if _deepseek is None:
        _deepseek = openai.OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"],
                                  base_url="https://api.deepseek.com")
    return _deepseek


_NUDGE = ("[Continue: now give Phil your full spoken reply — respond to his last "
          "attempt first (what the tone-ear heard, what was right, what to fix), "
          "then whatever comes next. Plain speakable prose.]")

# Everything the brain says gets spoken by TTS; an emoji comes out as noise and
# a "↓" comes out as the words "down arrow" (2026-07-06). The prompt forbids
# them, but models leak — so strip at the door, every provider: emoji planes
# plus arrows, technical, geometric shapes, dingbats, misc symbols.
_EMOJI_RE = re.compile("[←-⇿⌀-⏿■-◿"
                       "\U0001F000-\U0001FAFF☀-➿⬀-⯿"
                       "\U0001F1E6-\U0001F1FF️‍❤]")


def _run_brain_claude(state, system, convo):
    msgs, reply, tin, tout = list(convo), "", 0, 0
    for _ in range(6):
        # thinking disabled on purpose: Sonnet 5 runs ADAPTIVE thinking when the
        # param is omitted — it silently burned ~800 tokens/turn, blew the
        # max_tokens cap, and starved the tool calls (2026-07-03). Voice latency
        # budget says: no thinking, fix quality via the prompt.
        resp = _claude.messages.create(model=BRAIN_MODEL, max_tokens=900,
                                       thinking={"type": "disabled"},
                                       system=system, messages=msgs, tools=TOOLS)
        tin += resp.usage.input_tokens; tout += resp.usage.output_tokens
        if resp.stop_reason != "tool_use":
            reply = "".join(b.text for b in resp.content if b.type == "text").strip()
            break
        msgs.append({"role": "assistant", "content": resp.content})
        msgs.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": b.id,
             "content": _run_tool(state, b.name, b.input)}
            for b in resp.content if b.type == "tool_use"]})
    if not reply:
        # The silent-turn bug (2026-07-03): tools ran, no text came back, and the
        # tutor said nothing into the voice loop. Force one prose-only round.
        resp = _claude.messages.create(model=BRAIN_MODEL, max_tokens=500, system=system,
                                       thinking={"type": "disabled"},
                                       messages=msgs + [{"role": "user", "content": _NUDGE}],
                                       tools=TOOLS, tool_choice={"type": "none"})
        tin += resp.usage.input_tokens; tout += resp.usage.output_tokens
        reply = "".join(b.text for b in resp.content if b.type == "text").strip()
    log.info("brain claude turn: %s in / %s out tokens", tin, tout)
    return reply or "Say that once more for me?"


def _run_brain_oai(client, model, max_param, label, state, system, convo, extra=None):
    """OpenAI-dialect tool loop — serves deepseek and gpt. NB gpt-5.x models
    take max_completion_tokens where deepseek takes max_tokens."""
    oai_tools = [{"type": "function", "function": {
        "name": t["name"], "description": t["description"],
        "parameters": t["input_schema"]}} for t in TOOLS]
    msgs = [{"role": "system", "content": system}] + list(convo)
    reply, tin, tout = "", 0, 0
    extra = extra or {}
    for _ in range(6):
        resp = client.chat.completions.create(model=model, messages=msgs,
                                              tools=oai_tools, **{max_param: 900}, **extra)
        if resp.usage:
            tin += resp.usage.prompt_tokens; tout += resp.usage.completion_tokens
        m = resp.choices[0].message
        if not m.tool_calls:
            reply = (m.content or "").strip()
            break
        msgs.append({"role": "assistant", "content": m.content or "",
                     "tool_calls": [tc.model_dump() for tc in m.tool_calls]})
        for tc in m.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except ValueError:
                args = {}
            msgs.append({"role": "tool", "tool_call_id": tc.id,
                         "content": _run_tool(state, tc.function.name, args)})
    if not reply:
        resp = client.chat.completions.create(model=model, **{max_param: 500},
                                              messages=msgs + [{"role": "user", "content": _NUDGE}])
        reply = (resp.choices[0].message.content or "").strip()
    log.info("brain %s turn: %s in / %s out tokens", label, tin, tout)
    return reply or "Say that once more for me?"


_PAGE_NAME = {"deepseek": "deepseek", "gpt": "openai", "claude": "anthropic"}


def _brain_once(provider, state, system, convo):
    if provider == "deepseek":
        return _run_brain_oai(_ds(), DEEPSEEK_MODEL, "max_tokens", "deepseek",
                              state, system, convo)
    if provider == "gpt":
        # NB: gpt-5.4-mini 400s on reasoning_effort combined with function
        # tools, so it runs at default effort (~19s/turn) — acceptable for a
        # leg that only serves while deepseek is down
        return _run_brain_oai(_oai, GPT_MODEL, "max_completion_tokens", "gpt",
                              state, system, convo)
    return _run_brain_claude(state, system, convo)


def _brain(user_text, ear_line, activity="turn"):
    convo = _load_convo()
    convo.append({"role": "user", "content": f"{user_text}\n\n{ear_line}"})
    chain = [BRAIN_PROVIDER] + [p for p in BRAIN_CHAIN if p != BRAIN_PROVIDER]
    last_err = None
    for provider in chain:
        # fresh state per attempt: a provider that fails mid-turn discards its
        # half-done tool writes instead of double-applying them on the retry
        state = learner.load()
        learner.touch_day(state)
        system = SYSTEM + "\n\n# Current learner state\n" + learner.snapshot(state)
        try:
            reply = _brain_once(provider, state, system, convo)
        except Exception as e:
            page_if_billing(_PAGE_NAME[provider], e)
            log.warning("brain %s failed (%s) — trying next provider",
                        provider, str(e)[:150])
            last_err = e
            continue
        reply = _EMOJI_RE.sub("", reply).strip() or reply
        learner.record_activity(state, activity)
        learner.save(state)
        convo.append({"role": "assistant", "content": reply})
        _save_convo(convo)
        return reply
    raise HTTPException(502, f"every tutor brain failed; last: {str(last_err)[:200]}")


@app.get("/api/state")
async def get_state():
    return learner.api_view(learner.load())


# ── The deterministic learning systems ─────────────────────────────────────────
# Everything below runs without the tutor brain: the curriculum map, grammar
# unlocks, self-serve SRS reviews, the placement test, and reading/listening
# practice are plain functions over the same learner state the brain maintains,
# so a dead API key never blocks studying — and the brain hears about all of it
# through the state snapshot (learner.record_activity).

@app.get("/api/curriculum")
def curriculum_view():
    state = learner.load()
    idx = learner.speaking_stage(state)
    learned = learner.learned_count(state)
    stages = []
    for s in curriculum.STAGES:
        nxt = (curriculum.STAGES[s["idx"] + 1]["threshold"]
               if s["idx"] + 1 < len(curriculum.STAGES) else None)
        if s["idx"] < idx:
            prog = 1.0
        elif s["idx"] > idx:
            prog = 0.0
        else:
            span = (nxt - s["threshold"]) if nxt else 1
            prog = min(1.0, max(0.0, (learned - s["threshold"]) / max(1, span)))
        stages.append({**s, "state": "done" if s["idx"] < idx else
                       "current" if s["idx"] == idx else "locked",
                       "progress": round(prog, 3)})
    return {"stages": stages,
            "grammar": curriculum.grammar_for(idx),
            "writing_rungs": curriculum.WRITING_RUNGS,
            "position": {"stage_idx": idx, "stage": curriculum.STAGES[idx]["id"],
                         "writing_rung": learner.writing_rung(state),
                         "learned": learned,
                         "placement": state.get("placement")}}


@app.get("/api/review/queue")
def review_queue():
    state = learner.load()
    due = learner.due_words(state)
    return {"due": due[:20], "total": len(due)}


@app.post("/api/review/grade")
def review_grade(payload: dict):
    try:
        hanzi, grade = str(payload.get("hanzi", ""))[:20], int(payload.get("grade"))
    except (TypeError, ValueError):
        raise HTTPException(400, "grade must be an integer 0-5")
    if grade not in (0, 1, 2, 3, 4, 5):
        raise HTTPException(400, "grade must be 0-5")
    with learner.txn() as state:
        msg = learner.grade_word(state, hanzi, grade)
        if "not in the vocab list" in msg:
            raise HTTPException(404, msg)
        learner.record_activity(state, "review", hanzi, grade)
        learner.touch_day(state)
        out = {"result": msg, "remaining": len(learner.due_words(state)),
               "recommend": learner.recommend(state)}
    return out


@app.post("/api/placement/start")
def placement_start():
    return {"items": curriculum.placement_public(),
            "pass_per_stage": curriculum.PASS_PER_STAGE}


@app.post("/api/placement/submit")
def placement_submit(payload: dict):
    try:
        answers = {str(k): int(v) for k, v in (payload.get("answers") or {}).items()}
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(400, "answers must map item ids to choice indices")
    result = curriculum.score_placement(answers)
    with learner.txn() as state:
        learner.set_placement(state, result)
        learner.record_activity(state, "placement", result["stage"])
        learner.touch_day(state)
        out = {**result, "recommend": learner.recommend(state)}
    return out


@app.get("/api/practice/{kind}")
def practice_items(kind: str, stage: str = ""):
    if kind not in ("reading", "listening"):
        raise HTTPException(404, "unknown practice kind")
    state = learner.load()
    sid = stage if stage in {s["id"] for s in curriculum.STAGES} \
        else curriculum.STAGES[learner.speaking_stage(state)]["id"]
    gen = curriculum.reading_practice if kind == "reading" \
        else curriculum.listening_practice
    return gen(state["vocab"], sid)


@app.post("/api/practice/result")
def practice_result(payload: dict):
    kind = payload.get("kind")
    if kind not in ("reading", "listening"):
        raise HTTPException(400, "unknown practice kind")
    try:
        right, total = int(payload.get("right", 0)), int(payload.get("total", 0))
    except (TypeError, ValueError):
        raise HTTPException(400, "right/total must be integers")
    with learner.txn() as state:
        learner.record_activity(state, kind, str(payload.get("stage", ""))[:4],
                                f"{right}/{total}")
        learner.touch_day(state)
        out = {"ok": True, "recommend": learner.recommend(state)}
    return out


@app.get("/api/settings")
def settings_get():
    return learner.load()["settings"]


@app.post("/api/settings")
def settings_set(payload: dict):
    with learner.txn() as state:
        out = learner.update_settings(state, payload)
    return out


@app.get("/api/recommend")
def recommend_view():
    return learner.recommend(learner.load())


# ── Textbook shelf (safe metadata only — see ingest.py) ────────────────────────
@app.get("/api/library")
def library_view():
    index = ingest.load_index()
    if not index:
        return {"books": [], "note": "no index yet — run ingest.py on the host "
                                     "against the refernce/ shelf"}
    return {"generated": index["generated"],
            "books": [{**{k: b[k] for k in
                          ("file", "title", "authors", "isbn13", "format",
                           "pages", "hsk_volumes", "stages")},
                       "n_sections": len(b["sections"]),
                       "sections": b["sections"][:40]}
                      for b in index["books"]]}


@app.get("/api/library/search")
def library_search(q: str = ""):
    return {"hits": ingest.search(ingest.load_index(), q)}


@app.post("/api/library/reindex")
def library_reindex():
    src = HERE / "refernce"
    if not src.is_dir():
        raise HTTPException(409, "refernce/ shelf not visible here — run "
                                 "`python ingest.py` on the host instead")
    index = ingest.scan(src)
    (DATA / "library_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1))
    return {"ok": True, "books": len(index["books"])}


# ── Speech synthesis: Heart + Mandarin, stitched ───────────────────────────────
# The client speaks sentence-by-sentence through /api/tts (LifeLog's TTS-queue
# pattern), so audio starts at the first sentence. Each request is segmented:
# hanzi runs (with CJK punctuation) AND tone-marked pinyin → OpenAI Mandarin
# voice; everything else → Heart. Pinyin routing matters: "mā... mǎ" is Latin
# text, and sending it to Heart (English phonemizer) produced toneless mush in
# the middle of a listening drill (2026-07-03). Segments synthesize in
# parallel, get normalized to 24k mono PCM, and are joined with a short gap.
# A small cache makes drilled words replay free.
_PY_TONED = "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛ"
# a hanzi/CJK run, or a whitespace-joined run of pinyin syllables where at
# least one carries a tone mark (matched with its neighboring plain syllables
# so "nǐ hǎo" or "mā... mǎ" travels as one Mandarin segment)
_ZH_RUN = re.compile(
    r"[㐀-鿿　-〿！-･]+"
    r"|(?:[A-Za-z%(py)s]*[%(py)s][A-Za-z%(py)s]*)(?:[\s.…]+[A-Za-z%(py)s]*[%(py)s][A-Za-z%(py)s]*)*"
    % {"py": _PY_TONED})
_GAP_PCM = b"\x00" * int(24000 * 2 * 0.09)          # 90ms between voice switches
_tts_cache, _TTS_CACHE_MAX = {}, 300

# tokens inside a Mandarin run: maximal hanzi runs OR maximal latin/pinyin runs
# (punctuation/space between them dropped) — used to spot lone-syllable drills.
_ZH_TOKEN = re.compile(r"[㐀-鿿]+|[A-Za-z%s]+" % _PY_TONED)


# ── Reference voice: real Tone Perfect clips for isolated syllables ─────────────
# For single syllables the corpus covers, "hear it correctly" is a real human
# clip (speaker FV1, the most tone-canonical voice in the LOSO eval) instead of
# TTS — top tone fidelity exactly where a perception drill lives or dies, and a
# recording can't drone-hallucinate the way short-hanzi TTS does. Words and
# sentences stay on TTS: stitched isolated clips lose sandhi/coarticulation and
# sound wrong. Ear and mouth then share one ground truth — the same corpus the
# tone classifier is graded against. Staged by spike/build_ref_voice.py into
# DATA/tone_perfect_ref/ (gitignored data mount); REF_VOICE=0 disables it.
class RefVoice:
    def __init__(self, root):
        self.root, self.hanzi, self.pinyin = root, {}, {}
        self.enabled = os.environ.get("REF_VOICE", "1") != "0"
        index = root / "index.json"
        if self.enabled and index.exists():
            d = json.loads(index.read_text())
            self.hanzi, self.pinyin = d["hanzi"], d["pinyin"]
            log.info("ref voice: %s — %d hanzi / %d syllables",
                     d.get("speaker"), len(self.hanzi), len(self.pinyin))
        else:
            log.info("ref voice: off (%s)",
                     "REF_VOICE=0" if not self.enabled else "no index at %s" % index)

    def clip(self, token):
        """Clip filename for a lone-syllable token, else None (leave it to TTS)."""
        if not self.enabled:
            return None
        return self.hanzi.get(token) or self.pinyin.get(token)


REF = RefVoice(DATA / "tone_perfect_ref")


def _ffmpeg(args, data):
    r = subprocess.run(["ffmpeg", *args], input=data, capture_output=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg: " + r.stderr.decode()[-160:])
    return r.stdout


def _to_pcm(audio_bytes):
    return _ffmpeg(["-i", "pipe:0", "-f", "s16le", "-ar", "24000", "-ac", "1", "pipe:1"],
                   audio_bytes)


def _synth_zh(text):
    resp = _oai.audio.speech.create(model=ZH_TTS_MODEL, voice=ZH_TTS_VOICE, input=text,
                                    instructions=ZH_TTS_STYLE, response_format="mp3")
    return _to_pcm(resp.content)


_PCM_BPS = 24000 * 2                       # bytes per second of our 16-bit mono PCM


def _synth_zh_guarded(text):
    """The OpenAI TTS occasionally hallucinates on short hanzi inputs — a long
    droning hum instead of speech (2026-07-06). No text we send needs more than
    ~1s per character; anything past that is garbage: retry once, then give the
    segment up (returns None) rather than play a 30-second drone mid-lesson."""
    cap = int(_PCM_BPS * (3.0 + 1.0 * len(text)))
    pcm = _synth_zh(text)
    if len(pcm) > cap:
        log.warning("zh tts drone: %.1fs for %d chars — retrying %r",
                    len(pcm) / _PCM_BPS, len(text), text[:40])
        pcm = _synth_zh(text)
    if len(pcm) > cap:
        log.warning("zh tts droned twice — dropping segment audio for %r", text[:40])
        return None
    return pcm


def _synth_en(text):
    r = httpx.post(f"{VOICE_URL}/tts", json={"text": text, "voice": HEART_VOICE},
                   timeout=60)
    r.raise_for_status()
    return _to_pcm(r.content)


def _synth_ref(fname):
    """A staged Tone Perfect clip -> our PCM. Missing file drops to silence
    (returns None) rather than killing the turn — build_ref_voice.py stages
    every referenced clip, so this is an ops-error guard, not a normal path."""
    path = REF.root / fname
    if not path.exists():
        log.warning("ref clip missing: %s", fname)
        return None
    return _to_pcm(path.read_bytes())


def _segment_pcm(kind, text):
    key = (kind, text)
    if key in _tts_cache:
        return _tts_cache[key]
    try:
        if kind == "ref":
            pcm = _synth_ref(text)
        elif kind == "zh":
            pcm = _synth_zh_guarded(text)
        else:
            pcm = _synth_en(text)
    except Exception as e:
        if kind == "ref":
            log.warning("ref clip failed, dropping segment: %s", str(e)[:120])
            return b""
        if kind == "zh":
            page_if_billing("openai", e)
            raise
        log.warning("heart tts failed, falling back to openai: %s", str(e)[:120])
        pcm = _synth_zh_guarded(text)         # keep the turn alive on voice-svc outage
    if pcm is None:                           # glitched audio: the text stays on
        return b""                            # screen, the segment goes silent —
                                              # and garbage never enters the cache
    if len(_tts_cache) >= _TTS_CACHE_MAX:
        _tts_cache.pop(next(iter(_tts_cache)))
    _tts_cache[key] = pcm
    return pcm


def _expand_zh(run):
    """A Mandarin run -> segments. Only a run that is a SINGLE token which is a
    lone corpus syllable becomes a real clip; anything else passes through to
    TTS with its text and punctuation intact. Single-token is the safe test:
    hanzi drills ("妈 麻 马 骂", "妈…马") already arrive as separate one-token
    runs, so they each swap in a clip — but a multi-syllable run stays on TTS,
    which is what we want, since space-separated pinyin is ambiguous between a
    drill ("mā má mǎ mà") and a word ("nǐ hǎo") and we must never chop a word
    into robotic isolated syllables (wrong sandhi, no coarticulation)."""
    tokens = _ZH_TOKEN.findall(run)
    if len(tokens) == 1:
        fname = REF.clip(tokens[0])
        if fname:
            return [("ref", fname)]
    return [("zh", run)]


# one bounded pool for all synthesis — a pool per call leaked thread churn
_TTS_POOL = ThreadPoolExecutor(max_workers=4)


def synthesize(text):
    """Text (possibly mixed EN/hanzi) -> mp3 bytes, or None if nothing speakable."""
    speakable = re.sub(r"\([^)]*\)", " ", text).strip()   # pinyin glosses are visual
    segs, pos = [], 0
    for m in _ZH_RUN.finditer(speakable):
        head = speakable[pos:m.start()].strip()
        if head and re.search(r"\w", head):
            segs.append(("en", head))
        segs.extend(_expand_zh(m.group().strip()))
        pos = m.end()
    tail = speakable[pos:].strip()
    if tail and re.search(r"\w", tail):
        segs.append(("en", tail))
    if not segs:
        return None
    pcms = list(_TTS_POOL.map(lambda s: _segment_pcm(*s), segs))
    pcm = _GAP_PCM.join(pcms)
    return _ffmpeg(["-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "pipe:0",
                    "-f", "mp3", "-b:a", "64k", "pipe:1"], pcm)


@app.post("/api/tts")
def tts_route(payload: dict):
    text = str(payload.get("text", ""))
    if len(text) > 2000:              # client speaks sentence-by-sentence; a
        raise HTTPException(413, "text too long")   # novel here is a bug or abuse
    audio = synthesize(text)
    if audio is None:
        raise HTTPException(400, "nothing speakable")
    return Response(content=audio, media_type="audio/mpeg")


_MAX_AUDIO = 20 * 1024 * 1024         # ~45s of webm is ~1MB; 20MB is a bug or abuse


@app.post("/api/turn")
def turn(audio: UploadFile = File(...)):
    blob = audio.file.read(_MAX_AUDIO + 1)
    if len(blob) > _MAX_AUDIO:
        raise HTTPException(413, "audio too large")
    wav = _webm_to_wav(blob)
    try:
        heard = _stt(wav)
        if not heard:
            return {"heard": "", "reply": None, "tones": None,
                    "error": "didn't catch any speech — try again"}
        ear = EAR.analyze(wav)        # one analysis serves both the UI chips
        reply = _brain(heard, "[spoken — mic turn] " + EAR.report(analysis=ear))
    finally:
        os.unlink(wav)
    return {"heard": heard, "tones": ear, "reply": reply}


@app.get("/api/hanzi/{char}")
def hanzi_data(char: str):
    """Stroke data for the handwriting pad (hanzi-writer-data), cached to disk
    forever — after a character is practiced once, the CDN can disappear and
    writing practice keeps working."""
    char = char[:1]
    if not char or not ("㐀" <= char <= "鿿"):
        raise HTTPException(400, "not a hanzi")
    cache = DATA / "hanzi-cache"
    cache.mkdir(parents=True, exist_ok=True)
    p = cache / f"{ord(char):x}.json"
    if not p.exists():
        r = httpx.get(f"https://cdn.jsdelivr.net/npm/hanzi-writer-data@2/{quote(char)}.json",
                      timeout=30)
        if r.status_code != 200:
            raise HTTPException(404, f"no stroke data for {char}")
        p.write_bytes(r.content)
    return Response(content=p.read_bytes(), media_type="application/json")


@app.post("/api/writing_result")
def writing_result(payload: dict):
    """Per-character pad results, recorded deterministically by the app —
    drives the Write tab's ladder status; the tutor separately hears the
    word-level [writing practice] report."""
    with learner.txn() as state:
        for r in (payload.get("results") or [])[:60]:
            if not isinstance(r, dict):
                continue
            ch = str(r.get("char", ""))[:1]
            try:
                mistakes = max(0, int(r.get("mistakes", 0)))
            except (TypeError, ValueError):
                continue
            if ch and "㐀" <= ch <= "鿿":
                learner.record_writing(state, ch, mistakes)
    return {"ok": True}


@app.post("/api/lesson_go")
def lesson_go():
    """The continue-lesson button: no speech, no typing — the tutor arrives
    already knowing what's next (state note + history) and just starts."""
    reply = _brain(
        "[lesson button] Phil tapped the continue-lesson button. Skip greetings "
        "and don't ask what he wants — say in one short line what today's work "
        "is, then start it (due reviews first). End with something for him to say.",
        "[button press — no audio this turn]", activity="lesson")
    return {"reply": reply}


@app.post("/api/turn_text")
def turn_text(payload: dict):
    """Typed turn — the writing channel (curriculum reading & writing track)."""
    text = (payload.get("text") or "").strip()[:2000]
    if not text:
        raise HTTPException(400, "empty message")
    reply = _brain(text, "[typed input — no tone-ear this turn]")
    return {"heard": text, "tones": None, "reply": reply}


@app.post("/api/reset")
async def reset():
    if CONVO.exists():
        CONVO.rename(DATA / "conversation.prev.json")
    return {"ok": True}


LOGIN_HTML = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>LanguageTutor</title><style>
body{background:#101418;color:#e8e4da;font:16px/1.5 system-ui;display:grid;
place-items:center;min-height:100vh;margin:0}
form{display:flex;flex-direction:column;gap:12px;width:min(320px,85vw)}
h1{font-size:22px;font-weight:600;margin:0 0 4px}
input,button{font:inherit;padding:10px 14px;border-radius:10px;border:1px solid #2c3440}
input{background:#181e26;color:inherit}
button{background:#3d6b52;color:#fff;border:0;cursor:pointer}
.err{color:#e07a5f;margin:0}</style></head><body>
<form method=post action=/auth/login>
<h1>语伴 LanguageTutor</h1><!--err-->
<input type=password name=password placeholder="Password" autofocus>
<button>Enter</button></form></body></html>"""
