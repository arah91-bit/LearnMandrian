# LanguageTutor

Voice-first AI language tutor (Mandarin first, Spanish later) with a local
"tone ear": a DSP pitch pipeline that actually hears lexical tones and feeds
structured pronunciation feedback to an LLM tutor brain — the thing
commercial voice-tutor apps can't do.

Architecture decisions and rationale: see `spike/RESULTS.md` (feasibility
spike, 2026-07-02). App scaffolding will mirror LifeLog's patterns
(voice orb UI, auth middleware, frozen-prod + hot-reload-test deploys at
`/srv/docker/languagetutor`).

Status: spike complete, ear validated. Waiting on the Tone Perfect dataset
(MSU) for real-speech training/eval before building the app proper.
