"""The tone ear — local DSP pitch analysis, no API, no cost, no audio LLM.

Same method the spike validated: two-pass adaptive Praat pitch tracking,
speaker-relative semitone contours, classifier over contour shape. Retrained
on Tone Perfect (MSU; 9,837 real clips, 6 speakers) — 92.8% tone ID on unseen
speakers (leave-one-speaker-out) vs 40% for a frontier audio model,
spike/RESULTS.md. A random forest replaced logistic regression here: real
speech's messier per-instance contours (esp. tone 3's creaky dip) need a
nonlinear model — logreg only reached 74% on the same real-speech data.
Trained at import from tone_train.json (regenerate via
spike/tone_perfect_eval.py against the Tone Perfect corpus).

v1 scope: each voiced run is scored as one syllable candidate. Isolated
syllables and short words score cleanly; long connected speech is reported as
such rather than guessed at — the tutor drills isolated items first anyway.
"""
import json
import pathlib

import numpy as np
import parselmouth
from sklearn.ensemble import RandomForestClassifier

HERE = pathlib.Path(__file__).parent
N_POINTS = 24
MAX_GAP_FRAMES = 14      # ~70ms creak/dropout tolerated inside one syllable
MIN_RUN_FRAMES = 12      # ~60ms of voicing to count as a syllable at all
LONG_RUN_S = 0.9         # longer than this is probably connected speech, not one
                         # syllable — drilled isolated syllables run 0.3–0.8s


def _f0_track(path):
    snd = parselmouth.Sound(str(path))
    rough = snd.to_pitch(time_step=0.005, pitch_floor=50, pitch_ceiling=700)
    rf = rough.selected_array["frequency"].astype(float)
    rf = rf[rf > 0]
    if len(rf) < 8:
        return None
    q25, q75 = np.percentile(rf, [25, 75])
    pitch = snd.to_pitch(time_step=0.005, pitch_floor=max(40.0, 0.72 * q25),
                         pitch_ceiling=min(700.0, 2.2 * q75))
    f0 = pitch.selected_array["frequency"].astype(float)
    f0[f0 == 0] = np.nan
    return f0


def _runs(f0):
    """Voiced runs (start, end) tolerating short interior gaps."""
    voiced = np.where(np.isfinite(f0))[0]
    if len(voiced) == 0:
        return []
    runs, start = [], voiced[0]
    for prev, cur in zip(voiced, voiced[1:]):
        if cur - prev > MAX_GAP_FRAMES:
            runs.append((start, prev))
            start = cur
    runs.append((start, voiced[-1]))
    return [(s, e) for s, e in runs if e - s + 1 >= MIN_RUN_FRAMES]


def _contour(f0, s, e):
    seg = f0[s : e + 1]
    idx = np.arange(len(seg))
    good = np.isfinite(seg)
    if good.sum() < MIN_RUN_FRAMES:
        return None
    seg = np.interp(idx, idx[good], seg[good])
    st = 12 * np.log2(seg / np.median(seg))
    return np.interp(np.linspace(0, len(st) - 1, N_POINTS), np.arange(len(st)), st)


class ToneEar:
    def __init__(self, train_file=HERE / "tone_train.json"):
        data = json.loads(pathlib.Path(train_file).read_text())
        self.clf = RandomForestClassifier(n_estimators=300, random_state=0, n_jobs=-1).fit(
            np.array(data["X"]), np.array(data["y"]))

    def analyze(self, wav_path):
        """{'syllables': [{'tone', 'confidence', 'duration'}...], 'note': str|None}"""
        f0 = _f0_track(wav_path)
        if f0 is None:
            return {"syllables": [], "note": "no voiced speech detected"}
        out, long_runs = [], 0
        for s, e in _runs(f0)[:8]:
            contour = _contour(f0, s, e)
            if contour is None:
                continue
            dur = (e - s + 1) * 0.005
            if dur > LONG_RUN_S:
                long_runs += 1
                continue
            proba = self.clf.predict_proba([np.append(contour, dur)])[0]
            t = int(np.argmax(proba)) + 1
            out.append({"tone": t, "confidence": round(float(proba[t - 1]), 2),
                        "duration": round(dur, 2)})
        note = None
        if long_runs:
            note = (f"{long_runs} stretch(es) of connected speech — per-syllable "
                    "tone scoring only works on isolated syllables/short words")
        return {"syllables": out, "note": note}

    def report(self, wav_path=None, analysis=None):
        """One-line bracketed summary for the tutor brain's context. Pass the
        analyze() result if you already have it — the pitch tracking is the
        expensive part, and re-running it per turn was pure waste."""
        a = analysis if analysis is not None else self.analyze(wav_path)
        if not a["syllables"]:
            return f"[tone-ear] {a['note'] or 'nothing scoreable'}"
        parts = [f"#{i+1} tone{s['tone']} ({int(s['confidence']*100)}%)"
                 for i, s in enumerate(a["syllables"])]
        line = f"[tone-ear] heard {len(a['syllables'])} syllable(s): " + ", ".join(parts)
        if a["note"]:
            line += f" — {a['note']}"
        return line
