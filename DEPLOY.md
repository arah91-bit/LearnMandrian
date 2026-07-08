# LanguageTutor — dev/prod workflow (mirrors LifeLog's)

| | URL | Dir | Branch | Mode |
|---|---|---|---|---|
| **Test** | testlanguagetutor.arahub.org | `/srv/docker/languagetutor-test` | `dev` | hot-reload (source bind-mounted) |
| **Prod** | (later, once worth freezing) | `/srv/docker/languagetutor` | `main` | frozen image |

Repo home: `/home/phil/PersonalProjects/LanguageTutor` (main); the test dir is a linked
`dev` worktree. Edit HERE (`/srv/docker/languagetutor-test`), commit on `dev`; `main`
fast-forwards at ship time.

- Compose service `languagetutor-test` in `/srv/docker/docker-compose.yml` (project
  `docker`). API keys ride `/srv/docker/lifelog.env`; the tutor's own secrets
  (`TUTOR_PASSWORD`, `TUTOR_SESSION_SECRET`, `BRAIN_PROVIDER`) live in
  `/srv/docker/languagetutor.env`.
- **Brain chain:** `BRAIN_PROVIDER` (deepseek, the cheap default) is tried first,
  then the rest of deepseek → gpt → claude on ANY failure — one dead key never
  stops a lesson; billing failures also page Pushbullet. STT falls back from
  OpenAI to the shared voice container's local Whisper the same way.
- Learner data (conversation, future lesson state): `/home/phil/PersonalProjects/LanguageTutor-data` → `/data`.
- **Reference voice** (real Tone Perfect clips played for isolated-syllable
  drills instead of TTS): staged under `/data/tone_perfect_ref/` (1,640 FV1
  clips + `index.json`) by `spike/build_ref_voice.py`, run once against the
  Tone Perfect corpus. It's data, not image — lives in the `/data` mount, so
  **prod needs the same dir populated** (rerun the script pointed at prod's
  data dir, or copy the folder over). `REF_VOICE=0` disables it (falls back to
  TTS everywhere). The corpus itself is git- and docker-ignored (305 MB).
- **Deterministic learning systems** (2026-07-08): `curriculum.py` (stages,
  grammar unlocks, placement, practice generators) and `ingest.py` (textbook
  shelf metadata index) are bind-mounted like the other modules. Reviews,
  placement and practice run with NO API keys — only the tutor brain, STT and
  TTS need them. The shelf index is built on the HOST (the container can't see
  `refernce/`): `python ingest.py` with `DATA_DIR` pointed at the data mount;
  rerun it when the shelf changes. It stores titles/TOCs/page numbers only —
  never book text — and lives in `/data` (git-ignored), per the textbook rules.
- After editing `app.py`/`learner.py`/`curriculum.py`/`ingest.py`/`tone_ear.py`/`api_alerts.py`: `docker restart languagetutor-test`
  — single-file bind mounts go stale on atomic-rename saves. `static/` and
  `tutor_prompt.md` hot-reload (dir mount / uvicorn --reload-include).
- **Same gotcha applies to `/srv/docker/Caddyfile`** (single-file mount into `caddy`):
  after editing it, `docker restart caddy` — a `caddy reload` inside the container
  re-reads the STALE file and silently no-ops your change.
- Whole app is behind the auth cookie (`lt_session`): verify endpoints from inside
  the container (`docker exec languagetutor-test python -c "import app; ..."` with
  `app._cookie_value()`), not by raw curl — unauthenticated paths get the login page.
- Architecture ground truth: `spike/RESULTS.md`. The tone ear is local DSP on purpose;
  keep audio LLMs out of the tone-judging path (measured: 40% vs our 93%, real
  speakers, leave-one-speaker-out on Tone Perfect).
