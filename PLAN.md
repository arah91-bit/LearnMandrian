# PLAN.md — Zero to fluent, with small gaps the whole way

This is the content roadmap for LanguageTutor, written as a handoff: any agent
picking up a workstream below should be able to start from this file alone.
The product goal is a single sentence: **a learner who starts from absolute
zero and does what the app recommends every day is never stuck, never lost,
and never faces material with a gap in it — all the way to HSK6-level
fluency maintenance.** People learn best when each step is small; gaps are
bugs, and this repo treats them as test failures.

---

## 0. Execution header — the active run, no guesswork

**Active scope (Phase 1):** a gapless beginner arc, judged holistically against
the full path. Concretely, in order: WS1 phase B (seeds through S3 ≥ 450),
WS2 (reader R0–R3 to target depth, including the eight sketched texts),
WS3 (writing W0–W2 filled), WS4 (grammar S1–S3 + coverage test). While doing
it, keep the whole-path skeleton in view: the HSK Standard Course volumes 1–9
are the roadmap for everything after the beginner arc — map stages to volumes
as you go so later phases inherit a coverage outline, not a blank page.

**Approved source map** (owner-approved 2026-07-09; paraphrase, never copy):

| Source (in `refernce/`) | Use for | How |
|---|---|---|
| HSK Standard Course, 9 volumes (one PDF) | WS1 vocab scenes & sequence, WS2 text topics & difficulty curve, WS4 grammar order — the master roadmap | The PDF is SCANNED (no text layer). Volume boundaries are in the library index. Extract pages as images (pypdf image extraction or `pdftoppm` to the scratchpad) and READ them; take lesson sequence, topic lists, and word inventories as structure; re-author all prose yourself |
| Routledge Manual (Hu Bo, EPUB) | WS4 grammar inventory (its 语法/词汇 chapter TOCs), WS3 character pedagogy, punctuation | Text extracts fine; mine terminology lists and method, write our own explanations |
| Navarre, tech-enhanced teaching (PDF) | WS5 listening/literacy method | Chapter 5 has a text layer; method only |
| 对外汉语教学理论与实践 (PDF, zh) | Background theory | Optional; no text layer confirmed |

Official HSK word/grammar lists are published facts — use them freely as
checklists; the shelf is for sequencing and topics. **Never copy or closely
paraphrase running text** (dialogues, stories, example sentences): read,
close the source, write your own.

**Commands:** tests `~/PersonalProjects/LanguageTutor/.venv/bin/python -m
pytest tests/ -q` · lint `.../bin/ruff check .` (3 pre-existing E702s in
app.py stay) · JS: extract `<script>` from index.html, `node --check`.

**Scratch instance (never verify against live data):** write a wrapper script
in the session scratchpad and a `.claude/launch.json` pointing at it (delete
launch.json when done — never commit it):

```bash
#!/bin/bash
set -a; source /srv/docker/lifelog.env; set +a     # real API keys (dev use)
export DATA_DIR=<scratchpad>/data                  # fresh dir = fresh app
export TUTOR_PASSWORD=verify-pass TUTOR_SESSION_SECRET=verify-secret
export TUTOR_USER=arah91 TUTOR_USER_NAME=Phil      # bootstrap creates the account
export VOICE_URL=http://<voice-container-ip>:8001 BRAIN_PROVIDER=deepseek
exec ~/PersonalProjects/LanguageTutor/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8100
```

**Live user data policy:** `/home/phil/PersonalProjects/LanguageTutor-data`
(esp. `users/arah91/state.json`, activity log, tone stats, session summaries)
MAY BE READ for insight into real usage — which words fail, where sessions
stall, what the tutor planned. NEVER write to it, except an explicitly
agreed migration (document it in the commit message).

**Deploy target & backup:** target is this directory's live test container
(`docker restart languagetutor-test` for .py edits; rebuild+recreate for
Dockerfile/compose changes; smoke-test with `app.cookie_for('arah91')` from
inside the container). **Before any substantive run: push a backup** —
remote `origin` is `github-learnmandarin:arah91-bit/LearnMandrian.git`
(SSH alias in `~/.ssh/config`). Push your branches by name; NEVER force-push
and never touch `origin/main` (it is an unrelated early snapshot).

**Tests policy (owner delegated, decided):** invariant-first. If the content
type has an invariant, extend/point the test at the new target FIRST, then
write content until green. New content types land format + first batch +
their invariant in the same commit. Allowlists only shrink.

**Definition-of-done template:** every workstream ends with (1) named tests
green, (2) counts hit, (3) a browser walkthrough of the changed flow on the
scratch instance, (4) deploy + container-internal smoke test, (5) a commit
whose message says what a learner can now do that they couldn't.

---

## 1. Ground rules (read before touching anything)

- **Original content only — with an approved source map (§0).** The
  `refernce/` shelf (spelling intentional) is PRIVATE curriculum guidance:
  mine it for sequencing, coverage, topics, and method (owner-approved:
  paraphrase, don't copy). Word lists and grammar inventories are facts;
  running text — dialogues, stories, example sentences — is never copied or
  closely paraphrased: read, close the source, write your own. Extracts stay
  in the scratchpad; the ingestion index (safe metadata only) lives in the
  data mount; neither ever enters git.
- **The invariants are law.** `tests/` encodes the no-gap doctrine (§5). New
  content must keep them green; new content TYPES must ship with new
  invariants. Never grow an allowlist to make a test pass — shrink them.
- **Work on a feature branch**, small commits, run `python -m pytest tests/`
  and `ruff check .` before committing (venv:
  `~/PersonalProjects/LanguageTutor/.venv`). Verify UI changes in a real
  browser against a scratch instance (see §8), never against the live
  container's data.
- **Deploy notes are in DEPLOY.md.** Single-file bind mounts go stale on
  atomic saves — `docker restart languagetutor-test` after editing `.py`
  files; `static/` hot-reloads. New modules need a compose mount + Dockerfile
  COPY + container recreate.
- **Voice is identity.** Everything the learner meets should be hearable:
  tappable words, playable sentences, real Tone Perfect clips for isolated
  syllables. If you add content, wire its audio path (usually free: `/api/tts`
  handles hanzi; single syllables get corpus clips automatically).

## 2. Architecture orientation (where things live)

| File | Owns |
|---|---|
| `app.py` | FastAPI routes, auth/users, LLM tutor loop (ears/brain/mouth), TTS stitching |
| `learner.py` | Per-user state (JSON), SM-2 SRS, stage derivation, recommendations, snapshot for the tutor |
| `curriculum.py` | Speaking stages S0–S7, grammar points, SEED vocabulary per stage, placement test, reading/listening practice generators |
| `reader.py` | The graded reader: levels R0–R6, tokenized original texts, unlock/progress logic |
| `users.py` | Accounts, scrypt hashes, bootstrap, per-user data dirs |
| `tone_ear.py` | Local DSP tone classifier (do NOT put audio LLMs in this path) |
| `ingest.py` | Reference-shelf metadata index (safe metadata only) |
| `static/index.html` | The entire frontend (vanilla JS, single file, tabs: Learn/Talk/Read/Plan/Words/Write/Progress) |
| `curriculum.md`, `tutor_prompt.md` | The LLM tutor's prose playbook ({learner} is substituted per user) |
| `tests/` | The invariants. Start here to understand what "complete" means |

The LLM tutor (Talk tab) is the ceiling of the experience but NOT the load-
bearing floor: every deterministic system (reader, SRS, placement, practice,
writing pad) must work with no API keys, because that's what "never stuck"
means when a key dies.

## 3. Pedagogy — what the reference shelf teaches (our own words)

From the Routledge CFL manual (Hu Bo), the technology-enhanced teaching book
(Navarre), and the HSK Standard Course's structure (used as a coverage map,
never as a source of text):

1. **识字 binds three things**: form, sound, meaning. Every exposure should
   carry all three (our tap-gloss + audio + hanzi does this; keep it true).
2. **Comprehensible input**: novice reading is isolated words and formulaic
   sentences; a text with unknown, unglossed words is not input, it's noise.
   Hence the taught-before-used invariant.
3. **Cumulative knowledge**: components and known characters make new ones
   cheap (大+人=大人, 二+月=二月). Teach the combining insight explicitly and
   lean on it — the invariant's "compositional" rule encodes it.
4. **循环练习 — recycling**: words must recur in real text, not just in the
   SRS. Planned recurrence is a content requirement (tested).
5. **Retrieval first**: the learner produces before being shown. Flashcards
   reveal after the attempt; drills let the learner miss, then correct.
6. **Punctuation is literacy**: 。？、！：""《》 get taught at first sight
   (reader "Reading tip" notes). Extend as new marks appear.
7. **Pinyin is scaffolding**: ruby pinyin at the lowest levels, fading by
   level, always tappable — never abruptly removed.
8. **Small steps, one new thing at a time**: 3–8 new words per reader text,
   one grammar pattern per lesson beat, thresholds that unlock rather than
   walls that block.
9. **Coverage map**: HSK levels 1–6 define what a complete path must contain
   (topics, vocabulary scale ≈150/300/600/1200/2500/5000, grammar inventory).
   We mirror the COVERAGE, we write our own material.

## 4. The learner journey (the master ladder)

Four tracks advance in parallel, each with its own ladder, all feeding one
SRS deck and one recommendation engine. Placement can lift the speaking stage
at any time (Learn tab → Placement), so nobody is ever hard-stuck.

| Speaking | ≈HSK | Enter at (learned words) | Reader floor | Writing | Can-do exit |
|---|---|---|---|---|---|
| S0 tones | pre | 0 | R0 | W0 strokes | hear/say 4 tones on simple syllables |
| S1 survival | pre | 8 | R1 | W0 | greet, thank, part — all in Mandarin |
| S2 first scenes | HSK1 | 60 | R2 | W1 components | order, introduce family, buy |
| S3 your day | HSK2 | 200 | R3 | W1–W2 | narrate yesterday/today/tomorrow |
| S4 connected | HSK3 | 450 | R4 | W2 | 5-minute free conversation on a topic |
| S5 opinions | HSK4 | 900 | R5 | W2–W3 | argue a position; tell a full story |
| S6 wide world | HSK5 | 1800 | R6 | W3 | discuss news/culture; first 成语 |
| S7 maintenance | HSK6+ | 3500 | R7* | W3 | debate, humor, shadowing |

(*R7 does not exist yet — see WS2.)

**The daily loop** (what `learner.recommend()` walks the user through):
placement (once) → due SRS reviews → next reader text (new words join the
deck) → reading/listening practice → tutor lesson (new material) → writing
pad. Each completed step advances the recommendation; every step works
offline-from-the-LLM except the tutor lesson.

## 5. The no-gaps doctrine (invariants — existing and to add)

Existing (all in `tests/`, all green as of 2026-07-09):

- **Reader taught-before-used**: every word token is taught in its own or an
  earlier text, is a proper name, or is a compound of known characters.
- **Reader new-words-shown**: a text actually uses every word it teaches.
- **Reader recycling**: every R0/R1 word recurs in a later text (allowlist
  currently `{六,七,九}` — shrink it, never grow it).
- **Practice-passage coverage**: quiz passages may only use characters a
  learner at that stage has met (seeds + unlocked grammar examples).
- **Placement determinism**, seed pinyin/tone alignment, question validity.

To add (each is a small test + whatever content it takes to go green):

- **Threshold coverage** (WS1): cumulative deterministic vocabulary (seeds ∪
  reader words) at stage k ≥ the entry threshold of stage k+1, through S4.
  Current counts: S0 33, S1 74 (need 60 ✓), S2 189 (need 200 — 11 short),
  S3 270 (need 450), S4 327 (need 900). Beyond S4, fluency is measured by
  can-do checks, extensive reading, and the tutor — not word counts (§WS6).
- **Grammar example coverage** (WS4): grammar examples use only seed words
  from ≤ their stage, or carry inline glosses.
- **Writing-ladder soundness** (WS3): every rung char has stroke data in the
  hanzi cache; no duplicate chars across rungs; every W0–W2 char is also a
  seed word (writing chars are real vocabulary).
- **Reader level sizing** (WS2):每 level has ≥ its minimum text count.

## 6. Current inventory (2026-07-09, feature/curriculum-systems @ GitHub)

- Seeds: ~385 entries across S0–S6 (cumulative-with-reader: S1 74, S2 200,
  S6 ≈415). Threshold invariant green through entering S3.
- Reader: 23 texts, R0(5) R1(4) R2(5) R3(3) R4(3) R5(2) R6(1); ~130 words.
- Grammar: 33 points, S1–S6, original explanations + examples.
- Writing rungs: W0 11 chars, W1 8, W2/W3 empty (W2 is "your words", dynamic).
- Placement: S1–S6, 4 items each, server-scored, contiguous-pass.
- Practice: reading (passages+word items), listening (tone-ID + meaning).
- Tutor: full voice loop, tools writing the same state; brain fallback chain.
- Tests: 42 passing. Multi-user, per-user state, settings, textbook index: done.
- Backup remote: `origin` → `arah91-bit/LearnMandrian` (branches `dev`,
  `master`, `feature/curriculum-systems`; `origin/main` is unrelated — leave it).

## 7. Workstreams (sized, ordered, with acceptance criteria)

**WS1 — Vocabulary database to scale.** Grow SEEDS so the threshold-coverage
test passes through S4: S2 +≈15 (→ ≥200 cumulative), S3 +≈180 (HSK2/3 scenes:
directions, transport, house rooms, shopping details, school, nature, body,
jobs), S4 +≈570, staged by scene. At S4+ scale, curate in review batches:
frequency-informed lists are facts and fine to consult, but every entry is
hand-checked for pinyin/tones (the seed test catches syllable-count errors,
NOT wrong tones — check a sample against a dictionary each batch) and given a
plain-English gloss. Format: `("汉字", "pīn yīn", "gloss", [tones])`, pinyin
space-separated per syllable, 5=neutral. Mine scene lists from HSK volumes
1–3 first (§0 source map). **Done when (phase B):** threshold test asserts
through S3 entry→exit (`covered_through = "S3"`, needs cumulative ≥450) and
is green; no cross-stage duplicate hanzi (add this as a test); a 20-entry
random sample per batch dictionary-checked and noted in the commit message.
**Done when (phase C):** same through S4 (≥900).

**WS2 — Reader to full depth.** Targets: R0 8, R1 8, R2 10, R3 10, R4 8,
R5 6, R6 4, new R7 "长篇" (chaptered stories, 300–600 chars/chapter, 2–3
stories). Per-text rules: 3–8 new words (R6/R7 up to 10); sentence length
grows with level (R2 ≤8 chars, R4 ≤15, R6 free); every text pre-teaches its
new words; comprehension questions 2–4 with shuffled choices; punctuation
notes at first sight of a new mark; recycling — weave earlier words in
deliberately (numbers → prices/dates/ages/phone numbers; family → dialogues).
In-flight sketches (themes already validated against invariants): r1-5
component-magic (日+月=明, 女+子=好), r2-6 time (几点/半/起床 — move 几 here
from r3-3), r2-7 this/that (这/那/个/东西), r3-4 ages (岁/问), r3-5 where-to
(哪儿/学校/走), r4-4 my day (早上/晚上/睡觉/学习/汉语 — move 汉语 here from
r6-1), r5-3 birthday (生日/快乐/蛋糕/唱歌, sister turns 六 岁 → shrink the
recycling allowlist), r6-2 the horse's birthday (一起/月亮/星星). Keep texts
in ladder order in `TEXTS` (order IS the curriculum). **Done when:** level
counts hit R0 8 / R1 8 / R2 10 / R3 10 / R4 8 / R5 6 / R6 4 / R7 2 (add the
sizing test first, phased: beginner counts R0–R3 for Phase 1); all reader
invariants green; recycling allowlist = ∅; browser proof on the scratch
instance: open one NEW text per level, complete one end-to-end and watch its
words land in the due deck and the recommendation advance.

**WS3 — Writing ladder completion.** W0 += 四五六七八九水 (stroke-simple);
W1 += 也他她们田力男木林从 (each with a component story in the tile's
teaching flow); W2 becomes a curated ~40-char set of high-frequency word-
completers (天今去来见再中东西车手心门不是有…), each ≤8 strokes or built
from known parts; W3 stays composition but gets ENGINE support: dictation
exercises (TTS speaks a known phrase, learner types it, deterministic
check against hanzi) as a new practice kind. Also: `learner.writing_rung`
fallback should become "W3" once W0–W2 are all clean. **Done when:**
ladder-soundness test green (stroke data present, no dup chars across rungs,
every W0–W2 char is also a seed word); W0 ≥ 17 chars, W1 ≥ 16, W2 ≥ 30;
browser proof: a writing lesson queues new chars with audio, and one
dictation item completes end-to-end and records to the activity log.

**WS4 — Grammar to a complete inventory.** Target ≈120–150 points covering
the standard HSK1–5 grammar inventory (use the shelf's grammar chapter list
as the coverage map: measure words, 的/得/地, complements — result,
direction, potential, degree — comparisons, 把/被, questions, conjunction
pairs, aspect 了/过/着, discourse markers, register). Each point: pattern,
2–4 sentence explanation in the app's voice, 2–3 examples using only ≤stage
seed vocabulary (add the coverage test first, then write to it). Stage
mapping mirrors §4. **Done when (Phase 1 slice):** S1–S3 hold ≥ 45 points
total, mirroring the HSK1–2 grammar inventory (checklist from the Routledge
grammar TOC + HSK volume structure); the example-coverage test exists and is
green; browser proof: three new points open from the Learn tab with playable
examples; placement grammar items still generate and score.

**WS5 — Listening as a first-class track.** Now: generated tone-ID/meaning
items. Add: (a) listen-first mode for reader texts (hide text, play sentence
by sentence, then reveal and read — one flag in the reader UI, huge value);
(b) dictation (see WS3); (c) minimal-pair drills driven by the learner's own
tone-confusion stats (`tone_stats` already tracks them; Tone Perfect clips
already exist for all syllables). **Done when:** listen-first mode works on
one reader text in the browser; a dictation item completes; a confusion
drill launches from Progress; all three record to the activity log and the
recommendation engine rotates them.

**WS6 — Assessment beyond word counts.** (a) Placement: extend to 6 items
per stage and add an S7 section (成语, register, discourse). (b) Stage-exit
"can-do checks": a deterministic per-stage quiz (reading + listening +
dictation mix) that, when passed, lifts the derived stage the same way
placement does — this is the formal cure for "stuck between levels" at S4+
where word-count thresholds stop being the right measure. (c) Writing
assessment: per-rung clean-pass percentage already tracked; surface it in
Progress. **Done when:** a can-do check passes end-to-end in the browser and
the derived stage lifts; scoring has tests; failing the check recommends the
right remediation (reviews or reader texts), not a dead end.

**WS7 — Tutor integration.** The tutor should teach from the same database:
(a) inject a "stage word-plan: not yet taught" line (first ~8 seeds at the
current stage missing from the deck) into `learner.snapshot` — DONE in the
in-flight branch, verify it; (b) per-stage session scripts appended to
`curriculum.md` (opening ritual, drill shapes, can-do role-plays per stage);
(c) the tutor should be told what the learner just read (activity log
already carries it — extend the snapshot line with the last reader text
title). **Done when:** a scratch-instance lesson turn shows the tutor
teaching a word from the stage plan (transcript in the verification notes);
snapshot growth stays under ~150 tokens (check the brain token log lines).

**WS8 — Content integrity at scale.** As data grows: split `reader.py` texts
into `reader_texts.py` (data) vs logic if the file passes ~1500 lines; add a
`python -m pytest tests/ -q && ruff check .` pre-commit note to DEPLOY.md;
keep placement/practice generators fast (they re-derive per request). Audio
spot-check batch tool: a script that TTS-synthesizes any new seed batch and
flags drones (reuse `_synth_zh_guarded` logic) — catches bad pinyin by ear.

**WS9 — Beyond S6: maintenance content.** R7 chaptered stories; themed
conversation menus for the tutor (news/tech/culture prompts); 成语-of-the-day
feed drawing from an original 成语 set (story + example each); shadowing
exercises (play a sentence at natural speed, record, tone-ear + duration
compare). This is the "no finish line" tier — the app must keep offering
material forever.

**Order**: WS1(S2/S3 part) → WS2 → WS3 → WS4 → WS6(b) → WS5 → WS7 → WS1(S4)
→ WS9/WS8 as they become load-bearing. Rationale: the beginner arc must be
gapless first (that's where learners quit), assessments unstick the middle,
maintenance content lands last.

## 8. Verification playbook (every workstream, before "done")

1. `~/PersonalProjects/LanguageTutor/.venv/bin/python -m pytest tests/ -q`
2. `ruff check .` (three E702s in app.py are pre-existing style; leave them)
3. Frontend touched? Extract inline JS and `node --check` it; then run a
   scratch instance (wrapper script pattern: scratch `DATA_DIR`, dummy
   `TUTOR_PASSWORD`/`TUTOR_USER`, real API keys from `/srv/docker/lifelog.env`,
   `BRAIN_PROVIDER=deepseek`) and click through the changed flow in a real
   browser. Playwright MCP is broken on this host (needs sudo Chrome install)
   — use the Claude Preview tools.
4. Deploy to test: rebuild image if Dockerfile/requirements changed, restart
   (or recreate for new mounts), then smoke-test endpoints from inside the
   container with `app.cookie_for('<user>')`.
5. Live user data (`/home/phil/PersonalProjects/LanguageTutor-data`): read
   for insight, never write (full policy in §0).
6. Before a substantive run: push a backup branch to `origin` (§0).

## 9. Authoring reference (formats)

- **Seed entry**: `("汉字", "pīn yīn", "plain gloss", [tones])` — pinyin
  space-separated per syllable, tones 1–4, 5 = neutral; practical sandhi
  spelling for 不/一 (bú shì, yí gè) matches the rest of the app.
- **Reader sentence DSL**: `_s("汉|py|gloss 字|py|gloss 。", who="安娜")` —
  `_`→space inside pinyin/gloss; bare punctuation stands alone; speaker
  optional. Multi-syllable words are ONE token (你好|nǐ_hǎo|hello).
- **Reader text**: id `r<level>-<n>` (ids are progress keys — never renumber
  existing ones; append), title (zh) + title_en, intro (1–2 sentences, warm),
  optional note (reading tip), new_words (seed-entry format), sentences,
  en (full translation), qs (2–4, `a` = correct index; the UI shuffles).
- **Grammar point**: id kebab-case, stage, name ("是 — A is B" style),
  pattern, explain (2–4 sentences, app voice: concrete, no jargon), examples
  `(hanzi, pinyin, english)` with inline glosses for any word beyond stage
  seeds — until WS4's coverage test exists, gloss generously.
- **Voice**: warm, precise, second person, no filler. Cultural notes only
  when they attach to a word being taught.

## 10. Content change policy — cross-linked surfaces

When content changes, these move in the SAME commit (atomic, or the app
lies to the learner):

- The content + the tests that gate it (invariants extended first, §0).
- Reader text ids are progress keys: **never renumber or reuse** an existing
  id; append. If an existing text's substance changes (new words added), note
  it in the commit and clear affected users' done-markers for that id via a
  documented one-line migration (precedent: r0-1 on 2026-07-09).
- UI strings that NAME content (level titles, tab labels): update with the
  content. UI fallback constants in index.html (e.g. the LADDER literal) are
  first-paint only — update them when API shape changes, not per content batch.

These may LAG one commit, but never a release to the live container:

- `curriculum.md` / `tutor_prompt.md`: update only when stage semantics,
  track structure, or the tutor's behavioral contract changes — the brain
  reads state snapshots, not the content modules, so word-level changes
  don't touch it.
- `DEPLOY.md` / this file: whenever workflow or inventory facts change.

Known safe-by-construction: placement/practice items derive from seeds and
grammar at request time — content changes change the items, and that's fine
(scoring is recomputed server-side per submission; a learner mid-placement
across a deploy would get a mismatched sheet — rare enough to accept, noted
here so nobody "fixes" it into cached item banks).
