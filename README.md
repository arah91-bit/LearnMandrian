# LearnMandarin

A voice-first Mandarin tutor with a **local "tone ear"** — a DSP pitch pipeline
that actually *hears* lexical tones and feeds structured pronunciation feedback
to an LLM tutor brain. This is the thing "talk to the AI" voice-tutor apps
can't do: a frontier audio model, asked to name a Mandarin tone, gets it right
~40% of the time; the local pipeline here hits **~93% on unseen speakers**.

## Why split the ear from the brain?

Conversation goes speech-to-text → LLM → text-to-speech. Tone judgment can't
ride that path — the audio model that would hear the tone is the same one that's
bad at it. So tone perception is a separate, local, free DSP path whose reading
is injected into the LLM's context as structured data:

```
ears  = STT            (transcribes what was said)
brain = LLM (text)     (the actual tutoring intelligence)
mouth = TTS            (speaks the reply)
tone ear = tone_ear.py (local DSP — hears the tones, no API, no cost)
```

## The tone ear

`tone_ear.py` — two-pass adaptive Praat pitch tracking → longest voiced run
with creak-gap interpolation → speaker-relative semitone contour (24 points +
duration) → a random-forest classifier trained at import.

Trained and evaluated on **[Tone Perfect](https://tone.lib.msu.edu/)** (Michigan
State University): 9,837 isolated-syllable recordings from 6 native speakers.
Evaluation is **leave-one-speaker-out**, so every test clip is a voice the model
never trained on:

| Classifier | Accuracy (unseen speaker) |
|---|---|
| Random forest (shipped) | **92.8%** |
| Logistic regression | 74.1% |
| A frontier audio LLM asked to name the tone | ~40% |

Remaining confusion is the classic tone 2/3 and 3/4 pairs — the same ones human
listeners struggle with. See [`spike/RESULTS.md`](spike/RESULTS.md) for the full
methodology, the feasibility spike, and the audio-LLM baseline.

## Reference voice

For isolated-syllable drills, the "hear it correctly" audio is a **real human
recording** from the Tone Perfect corpus (one consistent speaker) rather than
TTS — highest tone fidelity exactly where a perception drill lives or dies, and
a recording can't hallucinate the way short-syllable TTS sometimes does. Words
and full sentences stay on TTS (stitched isolated syllables lose tone sandhi and
coarticulation and sound wrong). The classifier and the reference voice share
one ground truth: what the ear is graded against is what the learner hears.

`spike/build_ref_voice.py` builds a hanzi/pinyin → clip index from the corpus
(dropping polyphonic characters that can't be voiced unambiguously) and stages
the chosen speaker's clips into `$DATA_DIR/tone_perfect_ref/`.

## Running it

```bash
pip install -r requirements.txt
# provide OPENAI_API_KEY, ANTHROPIC_API_KEY, TUTOR_PASSWORD, TUTOR_SESSION_SECRET
uvicorn app:app --host 0.0.0.0 --port 8000
```

Or with Docker:

```bash
docker build -t learnmandarin .
docker run -p 8000:8000 --env-file .env -v "$PWD/data:/data" learnmandarin
```

The brain provider is configurable (`BRAIN_PROVIDER`), with fallback across
providers so one dead key never stops a lesson.

## The Tone Perfect data

The **raw Tone Perfect audio is not included** in this repo — it is Michigan
State University's dataset, redistributed only by them. Request it from
<https://tone.lib.msu.edu/>. What *is* included is derived from it and permitted
to share: `tone_train.json`, the anonymized pitch-contour features the
classifier trains on (no audio, speaker, syllable, or character metadata — just
9,837 normalized F0 vectors and their tone labels). Regenerate it, or build the
reference-voice pack, against your own copy of the corpus:

```bash
python spike/tone_perfect_eval.py    # LOSO eval + regenerate tone_train.json
python spike/build_ref_voice.py      # stage the reference-voice clips
```

## Acknowledgment

Tone data derived from **Tone Perfect: Multimodal Database for Mandarin
Chinese**, Michigan State University
([tone.lib.msu.edu](https://tone.lib.msu.edu/)). Please cite and follow their
terms of use if you build on this.
