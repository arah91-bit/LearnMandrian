"""Planted-error test: transplant a real tone contour from a donor clip onto
a recipient clip (same syllable, same voice), then check the classifier
detects the planted tone. This simulates a learner producing the wrong tone.

Non-circular: donor contours are real utterances, not classifier templates,
and the classifier is always trained without the recipient's voice.
"""
import json
import pathlib
import sys

import numpy as np
import pyworld as pw
import soundfile as sf

from tone_ear import build_dataset, extract_contour, N_POINTS
from sklearn.linear_model import LogisticRegression

HERE = pathlib.Path(__file__).parent
SYNTH = HERE / "synth"
SYNTH.mkdir(exist_ok=True)


def world_analyze(path):
    x, fs = sf.read(str(path))
    if x.ndim > 1:
        x = x.mean(axis=1)
    x = np.ascontiguousarray(x, dtype=np.float64)
    f0, t = pw.dio(x, fs)
    f0 = pw.stonemask(x, f0, t, fs)
    sp = pw.cheaptrick(x, f0, t, fs)
    ap = pw.d4c(x, f0, t, fs)
    return x, fs, f0, t, sp, ap


def donor_contour_st(path):
    """Semitone contour (re median) of the donor's voiced region."""
    res = extract_contour(path)
    return None if res is None else res[0]


def transplant(recipient, donor_st, out_path):
    x, fs, f0, t, sp, ap = world_analyze(recipient)
    voiced = f0 > 0
    n = voiced.sum()
    if n < 10:
        return False
    med = np.median(f0[voiced])
    st = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(donor_st)), donor_st)
    f0_new = f0.copy()
    f0_new[voiced] = med * 2 ** (st / 12)
    y = pw.synthesize(f0_new, sp, ap, fs)
    sf.write(str(out_path), y / max(1e-9, np.abs(y).max()) * 0.9, fs)
    return True


def main():
    manifest = json.loads((HERE / "manifest.json").read_text())
    X, y, voices, names = build_dataset()
    by_key = {}  # (syllable, voice) -> {tone: fname}
    for fname, meta in manifest.items():
        if fname in names:  # only clips with a valid contour
            by_key.setdefault((meta["syllable"], meta["voice"]), {})[meta["tone"]] = fname

    models = {}
    for v in sorted(set(voices)):
        tr = voices != v
        models[v] = LogisticRegression(max_iter=2000).fit(X[tr], y[tr])

    total = detected = kept_src = failed = 0
    confusion = {}  # (src, planted) -> [detected, n]
    for (syl, voice), tones in sorted(by_key.items()):
        for src, src_f in tones.items():
            for planted, don_f in tones.items():
                if planted == src:
                    continue
                donor_st = donor_contour_st(HERE / "audio" / don_f)
                if donor_st is None:
                    continue
                out = SYNTH / f"{syl}{src}_{voice}__as{planted}.wav"
                if not transplant(HERE / "audio" / src_f, donor_st, out):
                    failed += 1
                    continue
                res = extract_contour(out)
                if res is None:
                    failed += 1
                    continue
                feat = np.append(res[0], res[1]).reshape(1, -1)
                pred = int(models[voice].predict(feat)[0])
                total += 1
                key = (src, planted)
                confusion.setdefault(key, [0, 0])
                confusion[key][1] += 1
                if pred == planted:
                    detected += 1
                    confusion[key][0] += 1
                elif pred == src:
                    kept_src += 1
    print(f"planted-error cases: {total} (failed to synth/track: {failed})")
    print(f"detected planted tone: {detected}/{total} = {detected/total:.1%}")
    print(f"still heard original tone: {kept_src}/{total} = {kept_src/total:.1%}")
    print("detection by (original -> planted):")
    for (s, p), (d, n) in sorted(confusion.items()):
        print(f"  T{s}->T{p}: {d}/{n}")


if __name__ == "__main__":
    main()
