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

**Phase 1 — COMPLETE (2026-07-09, reviewed).** The gapless beginner arc
landed: seeds 618 (S3 exit coverage 512/450), reader 43 texts
(R0 8 / R1 8 / R2 10 / R3 11), writing W0 18 / W1 18 / W2 40, grammar 46
S1–S3 points, recycling allowlist ∅, tone-mark↔tone-number consistency
tested, W2 completion advances to W3. Review pass fixed three filler-quality
texts (r1-5, r1-6/林子 cut, r2-10, r3-11 rewritten as a coherent scene).

**Phase 2 — COMPLETE (2026-07-09, reviewed with corrections).** Landed:
S1–S4 can-do exit checks (server-scored, 80% + critical items, pass lifts the
derived stage, fail returns per-miss remediation pointing at reader texts /
grammar / reviews), dictation as a practice kind (NFKC + punctuation-stripped
answer matching), listen-first reader mode, tone drills fed by a detailed
per-attempt tone history (capped 200), tutor snapshot gains the stage
word-plan and last-read text, reader deepened to 57 texts through R7.
Review corrections: (1) REJECTED 360 machine-generated S4 "words" (cartesian
noun-pair products like 医生生日) that inflated threshold coverage — replaced
with ~115 hand-checked real words + 5 lexicalized collocations; S4 now sits at
an HONEST 673/900 and the threshold test asserts through S3 only. (2) Raw
learner-audio retention was unconditional — now opt-in via AUDIO_DEBUG=1
(default off; unbounded disk growth + quiet voice archiving is not a default).

**Standing content-authenticity rule (born from this review):** no
programmatic content generation. Every seed entry is a dictionary-attested
word or an explicitly marked lexicalized collocation; every reader sentence is
written by a person. Coverage numbers must be earned, not synthesized — a
threshold test that passes on fake words is worse than one that fails.

**Active scope (Phase 3): finish the middle, start the maintenance tier.**
In order:

1. **WS1 phase C-real — S4 to 900 with real words.** ~227 more hand-checked
   entries (HSK3/4 band scenes: emotions, workplace detail, travel, health,
   nature, quantities). Then move the threshold test cutoff to S4. Batch rule:
   dictionary spot-check 20 random entries per batch, note it in the commit.
2. **WS4 continuation — grammar S4–S6 to the full inventory.** From 59 points
   to ≈120: complements (potential 得/不, degree 极了/得很), 把/被 variants,
   越…越, 连…都, rhetorical patterns, discourse markers, register pairs.
   Extend the example character-coverage test to S4–S6 as points land.
3. **Progress surfacing (small, do early).** The Progress tab should show
   can-do results, tone-drill history (the data now exists in state), and
   writing-rung completion — a learner should SEE the ladder they're climbing.
4. **WS2/WS9 — upper reader + 成语 begin.** R5 6→8, R6 4→6, R7 2→4 chaptered
   texts; first original 成语 set (each: the idiom, its story retold in our
   own words at R6 vocabulary, one example) taught through R6/R7 texts.
5. **WS9 — shadowing (engine).** Play a native-speed sentence (TTS or ref
   clips), record the learner, compare tone-ear reading + duration; surface as
   a practice kind for S5+. Reuses the existing tone-drill recording plumbing.
6. **WS1 phase D (stretch) — S5 vocabulary toward 1800**, phased (target 1300
   this phase), same authenticity rules.

Per-item stop conditions follow the Phase 1/2 pattern: named tests green,
counts hit, one browser walkthrough per new flow, deploy + smoke after the
whole slice is reviewed. Same guardrails: invariant-first, scratch
verification, backup push, no force-push, `origin/main` untouched.

**Branch/deploy mode:** phase work happens on the feature branch, verified
against a scratch instance. Do not deploy after individual Phase 2 workstreams.
Deploying to the shared test container (`languagetutor-test`) happens only
after the whole Phase 2 slice is reviewed and local verification is green. It
is the owner's daily-driver dev instance and how real usage feedback happens.
Never deploy code with failing tests; never mutate live user data.

**Approved source map** (owner-approved 2026-07-09; paraphrase, never copy):

| Source (in `refernce/`) | Use for | How |
|---|---|---|
| HSK Standard Course, 9 volumes (one PDF) | WS1 vocab scenes & sequence, WS2 text topics & difficulty curve, WS4 grammar order — the master roadmap | The PDF is SCANNED (no text layer). Volume boundaries are in the library index. Extract pages as images (pypdf image extraction or `pdftoppm` to the scratchpad) and READ them; take lesson sequence, topic lists, and word inventories as structure; re-author all prose yourself |
| Routledge Manual (Hu Bo, EPUB) | WS4 grammar inventory (its 语法/词汇 chapter TOCs), WS3 character pedagogy, punctuation | Text extracts fine; mine terminology lists and method, write our own explanations |
| Navarre, tech-enhanced teaching (PDF) | WS5 listening/literacy method | Chapter 5 has a text layer; method only |
| 对外汉语教学理论与实践 (PDF, zh) | Background theory | Optional; no text layer confirmed |

Official HSK word/grammar lists are published facts — use them freely as
checklists; the shelf is for sequencing and topics. The 1–9 HSK Standard Course
set is the primary roadmap unless a clearly newer official/public checklist is
needed for gap checking. **Never copy or closely paraphrase running text**
(dialogues, stories, example sentences): read, close the source, write your
own. The private shelf may guide building, but it is not a code/data citation:
before any public GitHub handoff, scrub source-shelf filenames, Anna's Archive
references, scratch extracts, and private metadata from committed files. Code
and learner-facing data should read as original app content, not as references
to the shelf.

**Commands:** tests `~/PersonalProjects/LanguageTutor/.venv/bin/python -m
pytest tests/ -q` · lint `.../bin/ruff check --exclude spike .` (3
pre-existing E702s in app.py stay; archived spike scripts have additional
pre-existing lint) · JS: extract `<script>` from index.html, `node --check`.

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
inside the container). **Before any substantive run: push a backup** — remote
`origin` is `github-learnmandarin:arah91-bit/LearnMandrian.git` (SSH alias in
`~/.ssh/config`). Push branches by name; NEVER force-push and never touch
`origin/main` (it is an unrelated early snapshot).

**Tests policy (owner delegated, decided):** invariant-first. If the content
type has an invariant, extend/point the test at the new target FIRST, then
write content until green. New content types land format + first batch +
their invariant in the same commit. Allowlists only shrink.

**Definition-of-done template:** every workstream ends with (1) named tests
green, (2) counts hit, (3) a browser walkthrough of the changed flow on the
scratch instance, (4) dev-branch commit(s) whose messages say what a learner
can now do that they couldn't. Final Phase 2 owner review/handoff adds backup
check, deploy + container-internal smoke test if approved, and public-handoff
source scrub. `PLAN.md` is private working context and should be excluded from
any public GitHub handoff rather than scrubbed into a public artifact.

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
  and `ruff check --exclude spike .` before committing (venv:
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
- **Reader recycling**: every R0/R1 word recurs in a later text; allowlist is
  empty and must stay empty.
- **Practice-passage coverage**: quiz passages may only use characters a
  learner at that stage has met (seeds + unlocked grammar examples).
- **Placement determinism**, seed pinyin/tone alignment, tone-mark↔tone-number
  consistency, question validity.
- **Phase 1 coverage**: deterministic content covers leaving S3; S1–S3 grammar
  examples are stage-covered; W0–W2 writing ladder is sound; R0–R3 reader
  sizing is enforced.

To add (each is a small test + whatever content it takes to go green):

- **Threshold coverage** (WS1): cumulative deterministic vocabulary (seeds ∪
  reader words) at stage k ≥ the entry threshold of stage k+1, through S4.
  Current Phase 2 gap: leaving S4 must reach S5 entry (≥900 cumulative);
  post-Phase-1 count is 566/900.
- **Can-do checks** (WS6): deterministic S1–S4 stage-exit items, pass/fail
  scoring, stage lift, and targeted remediation.
- **Dictation/listen-first/confusion drills** (WS5): payload formats, scoring,
  activity logging, recommendation rotation, and tone-attempt detail history.
- **Reader level sizing continuation** (WS2): R4 ≥8, R5 ≥6, R6 ≥4, R7 ≥2 if
  the stretch goal is accepted.

## 6. Current inventory (2026-07-09 post-Phase-1, feature/curriculum-systems)

- Seeds: 618 entries across S0–S6; threshold invariant green through LEAVING
  S3 (exit coverage 512/450). Tone-mark↔tone-number consistency + cross-stage
  uniqueness tested.
- Reader: 43 texts, R0(8) R1(8) R2(10) R3(11) R4(3) R5(2) R6(1); recycling
  allowlist ∅. R4–R6 depth and R7 are Phase 2 (WS2 continuation).
- Grammar: 46 points S1–S3 (Phase 1 target met) + 13 S4–S6; example
  character-coverage tested for S1–S3.
- Writing rungs: W0 18, W1 18, W2 40 (soundness tested); W3 = composition
  (dictation engine is Phase 2/WS5); rung fallback advances to W3.
- Placement: S1–S6, 4 items each, server-scored, contiguous-pass.
- Practice: reading (passages+word items), listening (tone-ID + meaning).
- Tutor: full voice loop, tools writing the same state; brain fallback chain.
- Tests: 46 passing. Multi-user, per-user state, settings, textbook index: done.
- Backup remote: `origin` → `arah91-bit/LearnMandrian` (branches `dev`,
  `master`, `feature/curriculum-systems`; `origin/main` is unrelated — leave it).

## 7. Workstreams (sized, ordered, with acceptance criteria)

**WS1 — Vocabulary database to scale.** Phase B is done. Phase C grows SEEDS so
the threshold-coverage test passes through S4: post-Phase-1 cumulative content
leaves S4 at 566/900, so add roughly 335+ deterministic S4 words. Use HSK3/4
scenes: plans, work, city life, travel, social occasions, seasons/weather,
health, opinions, connectors, study/work routines, and story sequencing. Curate
in review batches: frequency-informed lists are facts and fine to consult, but
every entry is hand-checked for pinyin/tones (the seed test catches
syllable-count errors, NOT wrong tones) and given a plain-English gloss. Use the
existing Tone Perfect / `tone_ear.py` path for audio/tone sanity checks and TTS
spot checks; use dictionary/public-checklist lookup for lexical hanzi→pinyin
entries. Format: `("汉字", "pīn yīn", "gloss", [tones])`, pinyin space-separated
per syllable, 5=neutral. Mine scene lists from HSK volumes 3–4 first (§0 source
map), with newer public/official checklists only as gap checks. **Done when
(phase C):** threshold test asserts through S4 (`covered_through = "S4"`,
needs cumulative ≥900) and is green; cross-stage duplicate hanzi test remains
green; a 20-entry random sample per batch is pinyin/tone-checked and noted in
the commit message.

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
in ladder order in `TEXTS` (order IS the curriculum). **Done when (Phase 2
continuation):** level counts hit R4 8 / R5 6 / R6 4 (R7 2 as stretch); all
reader invariants green; recycling allowlist remains ∅; browser proof on the
scratch instance: open one NEW text per level, complete one end-to-end and watch
its words land in the due deck and the recommendation advance.

**WS3 — Writing ladder completion.** Phase 1 completed the W0–W2 soundness
slice and the W3 fallback. Do not reopen those rungs unless a content change
requires it. The remaining W3 engine work is now part of WS5: dictation
exercises where TTS speaks a known phrase, the learner types hanzi, and the
server checks a normalized answer plus configured alternate valid answers.
**Done when (future W3 polish):** ladder-soundness remains green; dictation
shares the WS5 activity-log/recommendation path; browser proof shows a known
phrase played, answered with an accepted variant, and recorded.

**WS4 — Grammar to a complete inventory.** Phase 1 completed the S1–S3 slice.
The future target remains ≈120–150 points covering the standard HSK1–5 grammar
inventory (use the shelf's grammar chapter list as the coverage map: measure
words, 的/得/地, complements — result, direction, potential, degree —
comparisons, 把/被, questions, conjunction pairs, aspect 了/过/着, discourse
markers, register). Each point: pattern, 2–4 sentence explanation in the app's
voice, 2–3 examples using only ≤stage seed vocabulary or explicit inline
glossing until the stage has the vocabulary. Stage mapping mirrors §4. **Done
when (future full inventory):** the grammar checklist is represented through
S5; example-coverage tests stay green; browser proof shows new points opening
from the Learn tab with playable examples; placement grammar items still
generate and score.

**WS5 — Listening as a first-class track.** Now: generated tone-ID/meaning
items. Add: (a) listen-first mode for reader texts as a reader mode flag with
activity logging (hide text, play sentence by sentence, then reveal and read);
(b) dictation (see WS3) with punctuation/spacing normalization and structured
alternate valid answers; (c) minimal-pair drills driven by the learner's own
tone-confusion history. Expand tone logging beyond pair counts: keep target
hanzi, pinyin, expected tones, heard tones, and enough context to pick the next
target word/syllable, and retain raw user audio in dev for tone/dictation
debugging. **Done when:** listen-first mode works on one reader text in the
browser; a dictation item accepts an alternate valid answer; a confusion drill
launches from Progress using a remembered target syllable/word; all three
record to the activity log and the recommendation engine rotates them.

**WS6 — Assessment beyond word counts.** (a) Placement: extend to 6 items
per stage and add an S7 section (成语, register, discourse) as a later polish
step. (b) Phase 2 priority: stage-exit "can-do checks", a deterministic
per-stage quiz for S1–S4. Store results separately from placement, let the
derived stage consider a pass, and use a practical scoring rule: about 80%
overall plus no missed critical items. Start with reading + listening items;
add dictation items after WS5 lands. A failed check must return targeted
remediation keyed to the failed skill/content (reviews, specific reader text,
listening, dictation, grammar), not just "try again." Build S1–S3 first; hold
S4 until WS1/WS2 create enough S4 content for a fair check if needed. (c)
Writing assessment: per-rung clean-pass percentage already tracked; surface it
in Progress when it becomes load-bearing. **Done when:** S1–S3 can-do checks
pass/fail end-to-end in the browser; scoring and remediation have tests; a pass
lifts the derived stage without overwriting placement history; S4 is either
implemented against sufficient S4 content or explicitly deferred until after
WS1/WS2 in the same Phase 2 slice.

**WS7 — Tutor integration.** The tutor should teach from the same database:
(a) inject a "stage word-plan: not yet taught" line (first ~8 seeds at the
current stage missing from the deck) into `learner.snapshot`; (b) per-stage
session scripts appended to `curriculum.md` (opening ritual, drill shapes,
can-do role-plays per stage); (c) the tutor should be told what the learner
just read (activity log already carries it — extend the snapshot line with the
last reader text title). Verification may use one or two real DeepSeek calls on
a scratch instance, but keep them minimal and do not let LLM checks replace
deterministic tests. **Done when:** a scratch-instance lesson turn shows the
tutor teaching a word from the stage plan and acknowledging the last reader
text when relevant (transcript in the verification notes); snapshot growth
stays under ~150 tokens (check the brain token log lines).

**WS8 — Content integrity at scale.** As data grows: split `reader.py` texts
into `reader_texts.py` (data) vs logic if the file passes ~1500 lines; add a
`python -m pytest tests/ -q && ruff check --exclude spike .` pre-commit note to DEPLOY.md;
keep placement/practice generators fast (they re-derive per request). Audio
spot-check batch tool: a script that TTS-synthesizes any new seed batch and
flags drones (reuse `_synth_zh_guarded` logic) — catches bad pinyin by ear.

**WS9 — Beyond S6: maintenance content.** R7 chaptered stories; themed
conversation menus for the tutor (news/tech/culture prompts); 成语-of-the-day
feed drawing from an original 成语 set (story + example each); shadowing
exercises (play a sentence at natural speed, record, tone-ear + duration
compare). This is the "no finish line" tier — the app must keep offering
material forever.

**Order**: Phase 1 is complete. Phase 2 order is WS6(b) S1–S3 can-do checks →
WS5 core listening/dictation/tone-history → WS7 tutor snapshot integration →
WS1 phase C S4 vocabulary → WS6(b) S4 can-do check if held back → WS2 R4–R6
depth (R7 stretch) → WS8/WS9 only as they become load-bearing. Rationale: first
unstick deterministic progression, then deepen the content those new checks
open.

## 8. Verification playbook (every workstream, before "done")

1. `~/PersonalProjects/LanguageTutor/.venv/bin/python -m pytest tests/ -q`
2. `ruff check --exclude spike .` (three E702s in app.py are pre-existing
   style; leave them)
3. Frontend touched? Extract inline JS and `node --check` it; then run a
   scratch instance (wrapper script pattern: scratch `DATA_DIR`, dummy
   `TUTOR_PASSWORD`/`TUTOR_USER`, real API keys from `/srv/docker/lifelog.env`,
   `BRAIN_PROVIDER=deepseek`) and click through the changed flow in a real
   browser. Playwright MCP is broken on this host (needs sudo Chrome install);
   use whatever browser/preview tooling is available in the session, or a
   manual browser walkthrough if no browser automation tool is exposed.
4. During Phase 2, stop at scratch-instance verification and dev-branch commits
   after each workstream. Deploy to `languagetutor-test` only after the whole
   Phase 2 slice is reviewed and local verification is green. Final handoff
   deploy: rebuild image if Dockerfile/requirements changed, restart (or
   recreate for new mounts), then smoke-test endpoints from inside the
   container with `app.cookie_for('<user>')`.
5. Live user data (`/home/phil/PersonalProjects/LanguageTutor-data`): read
   for insight, never write (full policy in §0).
6. At completion/handoff, verify the branch backup on `origin` (§0).
7. Before any public GitHub handoff, exclude `PLAN.md` and scrub private shelf
   references, extracted source notes, and Anna's Archive metadata from
   committed files.

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
