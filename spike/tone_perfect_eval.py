"""Retrain + evaluate the tone-ear classifier on Tone Perfect (MSU), the real
human-speaker corpus RESULTS.md flagged as the next step after the TTS spike.

9,840 isolated-syllable clips, 6 speakers (FV1-3, MV1-3), 410 syllables x
tones 1-4. Same feature pipeline as tone_ear.py (two-pass Praat pitch track,
longest voiced run, semitone-normalized 24-point contour + duration);
evaluation is leave-one-speaker-out so every test clip is an unseen voice,
same protocol as the original TTS-voice LOVO in spike/tone_ear.py.
"""
import json
import pathlib
import re
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from sklearn.linear_model import LogisticRegression

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

DATA = HERE.parent / "Tone perfect data set" / "tone_perfect_all_mp3" / "tone_perfect"
NAME_RE = re.compile(r"^([a-z]+)([1-4])_([A-Z0-9]+)_MP3\.mp3$")


def _extract(path_str):
    from tone_ear import _contour, _f0_track, _runs  # re-imported per worker

    path = pathlib.Path(path_str)
    m = NAME_RE.match(path.name)
    if not m:
        return None
    syllable, tone, speaker = m.groups()
    f0 = _f0_track(path)
    if f0 is None:
        return None
    runs = _runs(f0)
    if not runs:
        return None
    s, e = max(runs, key=lambda r: r[1] - r[0])
    contour = _contour(f0, s, e)
    if contour is None:
        return None
    dur = (e - s + 1) * 0.005
    return {
        "x": np.append(contour, dur).tolist(),
        "y": int(tone),
        "speaker": speaker,
        "syllable": syllable,
        "name": path.name,
    }


def build_dataset(cache=HERE / "tone_perfect_features.json"):
    if cache.exists():
        print(f"loading cached features from {cache}", file=sys.stderr)
        return json.loads(cache.read_text())
    files = sorted(str(p) for p in DATA.glob("*_MP3.mp3"))
    print(f"extracting features from {len(files)} clips...", file=sys.stderr)
    rows, skipped = [], 0
    with ProcessPoolExecutor() as pool:
        for i, res in enumerate(pool.map(_extract, files, chunksize=64)):
            if res is None:
                skipped += 1
            else:
                rows.append(res)
            if (i + 1) % 2000 == 0:
                print(f"  {i + 1}/{len(files)}", file=sys.stderr)
    print(f"extracted {len(rows)}, skipped {skipped}", file=sys.stderr)
    cache.write_text(json.dumps(rows))
    return rows


def main():
    rows = build_dataset()
    X = np.array([r["x"] for r in rows])
    y = np.array([r["y"] for r in rows])
    speakers = np.array([r["speaker"] for r in rows])
    names = [r["name"] for r in rows]

    print(f"dataset: {len(y)} clips, speakers={sorted(set(speakers))}")
    all_true, all_pred = [], []
    for held_out in sorted(set(speakers)):
        te = speakers == held_out
        tr = ~te
        lr = LogisticRegression(max_iter=2000, C=1.0).fit(X[tr], y[tr])
        pred = lr.predict(X[te])
        acc = np.mean(pred == y[te])
        print(f"held-out {held_out:6s}: logreg {acc:.1%}  (n={te.sum()})")
        all_true.extend(y[te])
        all_pred.extend(pred)

    all_true, all_pred = np.array(all_true), np.array(all_pred)
    pooled = np.mean(all_pred == all_true)
    print(f"\npooled leave-one-speaker-out: {pooled:.1%}  (n={len(all_true)})")
    print("confusion (rows=true tone, cols=predicted):")
    for t in (1, 2, 3, 4):
        row = [np.sum((all_true == t) & (all_pred == p)) for p in (1, 2, 3, 4)]
        print(f"  T{t}: {row}")

    print(f"\nfull-data fit for production tone_train.json: "
          f"{len(y)} samples, {len(set(speakers))} speakers, {len(set(r['syllable'] for r in rows))} syllables")


if __name__ == "__main__":
    main()
