"""Tone-ear spike: F0 contour extraction + tone classification.

Pipeline: wav -> parselmouth F0 track -> longest voiced run (creak gaps
interpolated) -> semitones re clip median -> resample to fixed length.
Evaluation is leave-one-voice-out so every test clip is an unseen speaker.
"""
import json
import pathlib
import sys

import numpy as np
import parselmouth
from sklearn.linear_model import LogisticRegression

HERE = pathlib.Path(__file__).parent
N_POINTS = 24
MAX_GAP_FRAMES = 14  # ~70ms of creak/tracking dropout allowed inside a run


def extract_contour(path):
    """Return (contour_semitones[N_POINTS], duration_s) or None if unvoiced."""
    snd = parselmouth.Sound(str(path))
    # two-pass (Hirst): wide first pass, then per-clip adaptive floor/ceiling
    rough = snd.to_pitch(time_step=0.005, pitch_floor=50, pitch_ceiling=700)
    rf = rough.selected_array["frequency"].astype(float)
    rf = rf[rf > 0]
    if len(rf) < 8:
        return None
    q25, q75 = np.percentile(rf, [25, 75])
    floor = max(40.0, 0.72 * q25)
    ceiling = min(700.0, 2.2 * q75)
    pitch = snd.to_pitch(time_step=0.005, pitch_floor=floor, pitch_ceiling=ceiling)
    f0 = pitch.selected_array["frequency"].astype(float)
    f0[f0 == 0] = np.nan
    voiced = np.where(np.isfinite(f0))[0]
    if len(voiced) < 12:
        return None
    # longest run of voiced frames tolerating short interior gaps
    runs, start = [], voiced[0]
    for prev, cur in zip(voiced, voiced[1:]):
        if cur - prev > MAX_GAP_FRAMES:
            runs.append((start, prev))
            start = cur
    runs.append((start, voiced[-1]))
    s, e = max(runs, key=lambda r: r[1] - r[0])
    seg = f0[s : e + 1]
    # interpolate interior dropouts (tone-3 creak)
    idx = np.arange(len(seg))
    good = np.isfinite(seg)
    if good.sum() < 12:
        return None
    seg = np.interp(idx, idx[good], seg[good])
    st = 12 * np.log2(seg / np.median(seg))
    contour = np.interp(
        np.linspace(0, len(st) - 1, N_POINTS), np.arange(len(st)), st
    )
    return contour, len(seg) * 0.005


def build_dataset():
    manifest = json.loads((HERE / "manifest.json").read_text())
    X, y, voices, names = [], [], [], []
    skipped = []
    for fname, meta in sorted(manifest.items()):
        res = extract_contour(HERE / "audio" / fname)
        if res is None:
            skipped.append(fname)
            continue
        contour, dur = res
        X.append(np.append(contour, dur))
        y.append(meta["tone"])
        voices.append(meta["voice"])
        names.append(fname)
    if skipped:
        print(f"skipped (unvoiced/too short): {skipped}", file=sys.stderr)
    return np.array(X), np.array(y), np.array(voices), names


def nearest_template(X_tr, y_tr, X_te):
    templates = {t: X_tr[y_tr == t, :N_POINTS].mean(axis=0) for t in sorted(set(y_tr))}
    preds = []
    for row in X_te:
        dists = {t: np.linalg.norm(row[:N_POINTS] - tpl) for t, tpl in templates.items()}
        preds.append(min(dists, key=dists.get))
    return np.array(preds)


def main():
    X, y, voices, names = build_dataset()
    print(f"dataset: {len(y)} clips, voices={sorted(set(voices))}")
    all_true, all_tpl, all_lr = [], [], []
    for held_out in sorted(set(voices)):
        te = voices == held_out
        tr = ~te
        tpl_pred = nearest_template(X[tr], y[tr], X[te])
        lr = LogisticRegression(max_iter=2000, C=1.0).fit(X[tr], y[tr])
        lr_pred = lr.predict(X[te])
        print(
            f"held-out {held_out:8s}: template {np.mean(tpl_pred == y[te]):.1%}"
            f"  logreg {np.mean(lr_pred == y[te]):.1%}  (n={te.sum()})"
        )
        all_true.extend(y[te]); all_tpl.extend(tpl_pred); all_lr.extend(lr_pred)
        for n, t, p in zip(np.array(names)[te], y[te], lr_pred):
            if t != p:
                print(f"    miss(logreg): {n} true={t} pred={p}")
    all_true, all_tpl, all_lr = map(np.array, (all_true, all_tpl, all_lr))
    print(f"\npooled: template {np.mean(all_tpl == all_true):.1%}  "
          f"logreg {np.mean(all_lr == all_true):.1%}")
    print("confusion (rows=true tone, cols=predicted, logreg):")
    for t in (1, 2, 3, 4):
        row = [np.sum((all_true == t) & (all_lr == p)) for p in (1, 2, 3, 4)]
        print(f"  T{t}: {row}")


if __name__ == "__main__":
    main()
