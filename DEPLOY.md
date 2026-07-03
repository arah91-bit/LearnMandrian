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
  (`TUTOR_PASSWORD`, `TUTOR_SESSION_SECRET`) live in `/srv/docker/languagetutor.env`.
- Learner data (conversation, future lesson state): `/home/phil/PersonalProjects/LanguageTutor-data` → `/data`.
- After editing `app.py`/`tone_ear.py`/`api_alerts.py`: `docker restart languagetutor-test`
  — single-file bind mounts go stale on atomic-rename saves. `static/` and
  `tutor_prompt.md` hot-reload (dir mount / uvicorn --reload-include).
- **Same gotcha applies to `/srv/docker/Caddyfile`** (single-file mount into `caddy`):
  after editing it, `docker restart caddy` — a `caddy reload` inside the container
  re-reads the STALE file and silently no-ops your change.
- Whole app is behind the auth cookie (`lt_session`): verify endpoints from inside
  the container (`docker exec languagetutor-test python -c "import app; ..."` with
  `app._cookie_value()`), not by raw curl — unauthenticated paths get the login page.
- Architecture ground truth: `spike/RESULTS.md`. The tone ear is local DSP on purpose;
  keep audio LLMs out of the tone-judging path (measured: 40% vs our 83%).
