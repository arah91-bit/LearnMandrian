"""LanguageTutor — voice-first Mandarin tutor.

Architecture (the whole point, see spike/RESULTS.md): NO voice-to-voice model.
- ears  = gpt-4o-transcribe (STT, pay-per-second)
- brain = claude-sonnet-5 (text — where the actual tutoring intelligence lives)
- mouth = gpt-4o-mini-tts (pay-per-character)
- tone ear = tone_ear.py, local DSP, free — the thing audio LLMs can't do (40%
  vs our 83%); its report is injected into the brain's context each turn.

Single-user app behind an auth cookie (LifeLog pattern): every path except
/healthz and /auth/login requires the session cookie; bare paths get the login
page, /api/* gets 401. Deploy notes in DEPLOY.md-to-be; test instance is
testlanguagetutor.arahub.org (compose service languagetutor-test).
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import pathlib
import re
import subprocess
import tempfile

import anthropic
import openai
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

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
TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = "nova"
TTS_STYLE = ("Warm, patient Mandarin tutor. Pronounce Chinese in clear standard "
             "Beijing Mandarin at a learner-friendly pace with exact lexical tones; "
             "English at a natural pace.")
MAX_MESSAGES = 40        # conversation window kept on disk / sent to the brain

SYSTEM = (HERE / "tutor_prompt.md").read_text()
EAR = ToneEar()
_oai = openai.OpenAI()
_claude = anthropic.Anthropic()


def _cookie_value():
    return hmac.new(SECRET.encode(), b"tutor-v1", hashlib.sha256).hexdigest()


class Auth(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if (path in ("/healthz", "/auth/login")
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


@app.post("/auth/login")
async def login(request: Request):
    form = await request.form()
    if not hmac.compare_digest(str(form.get("password", "")), PASSWORD):
        return HTMLResponse(LOGIN_HTML.replace("<!--err-->",
                            "<p class=err>Wrong password.</p>"), status_code=401)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("lt_session", _cookie_value(), max_age=90 * 86400,
                    httponly=True, secure=True, samesite="lax")
    return resp


@app.get("/")
async def index():
    return FileResponse(HERE / "static" / "index.html")


def _load_convo():
    return json.loads(CONVO.read_text()) if CONVO.exists() else []


def _save_convo(msgs):
    CONVO.write_text(json.dumps(msgs[-MAX_MESSAGES:], ensure_ascii=False, indent=1))


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
        raise HTTPException(502, f"speech-to-text failed: {str(e)[:200]}")


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


def _brain(user_text, ear_line):
    state = learner.load()
    learner.touch_day(state)
    convo = _load_convo()
    convo.append({"role": "user", "content": f"{user_text}\n\n{ear_line}"})
    system = SYSTEM + "\n\n# Current learner state\n" + learner.snapshot(state)
    msgs = list(convo)        # tool exchanges stay in-turn; disk keeps text only
    reply = ""
    try:
        for _ in range(6):
            resp = _claude.messages.create(model=BRAIN_MODEL, max_tokens=900,
                                           system=system, messages=msgs, tools=TOOLS)
            if resp.stop_reason != "tool_use":
                reply = "".join(b.text for b in resp.content if b.type == "text").strip()
                break
            results = [{"type": "tool_result", "tool_use_id": b.id,
                        "content": _run_tool(state, b.name, b.input)}
                       for b in resp.content if b.type == "tool_use"]
            msgs.append({"role": "assistant", "content": resp.content})
            msgs.append({"role": "user", "content": results})
        else:
            reply = "Let's pick that up again — say that once more?"
    except Exception as e:
        page_if_billing("anthropic", e)
        raise HTTPException(502, f"tutor brain failed: {str(e)[:200]}")
    learner.save(state)
    convo.append({"role": "assistant", "content": reply})
    _save_convo(convo)
    return reply


@app.get("/api/state")
async def get_state():
    return learner.api_view(learner.load())


def _tts(text):
    # Parentheticals are visual asides (pinyin glosses) — spoken they'd be noise.
    speakable = re.sub(r"\([^)]*\)", "", text).strip() or text
    try:
        resp = _oai.audio.speech.create(model=TTS_MODEL, voice=TTS_VOICE,
                                        input=speakable, instructions=TTS_STYLE,
                                        response_format="mp3")
        return base64.b64encode(resp.content).decode()
    except Exception as e:
        page_if_billing("openai", e)
        log.warning("tts failed (returning text-only turn): %s", str(e)[:200])
        return None


@app.post("/api/turn")
async def turn(audio: UploadFile = File(...)):
    wav = _webm_to_wav(await audio.read())
    try:
        heard = _stt(wav)
        if not heard:
            return {"heard": "", "reply": None, "tones": None,
                    "error": "didn't catch any speech — try again"}
        ear = EAR.analyze(wav)
        reply = _brain(heard, EAR.report(wav))
    finally:
        os.unlink(wav)
    return {"heard": heard, "tones": ear, "reply": reply, "audio": _tts(reply)}


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
