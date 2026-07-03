"""Generate isolated Mandarin syllables via OpenAI TTS for the tone-ear spike.

Each syllable is a full 4-tone minimal quadruplet, one common hanzi per tone,
so the TTS reads a single character in isolation with its lexical tone.
"""
import json
import os
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from api_alerts import page_if_billing
AUDIO = HERE / "audio"
AUDIO.mkdir(exist_ok=True)

ENV_FILE = "/srv/docker/lifelog.env"


def load_env():
    for line in pathlib.Path(ENV_FILE).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ[k.strip()] = v.strip()


# syllable -> {tone: hanzi}
QUADS = {
    "ma":   {1: "妈", 2: "麻", 3: "马", 4: "骂"},
    "yi":   {1: "一", 2: "姨", 3: "椅", 4: "意"},
    "shi":  {1: "诗", 2: "十", 3: "史", 4: "是"},
    "wu":   {1: "屋", 2: "无", 3: "五", 4: "物"},
    "ba":   {1: "八", 2: "拔", 3: "把", 4: "爸"},
    "tang": {1: "汤", 2: "糖", 3: "躺", 4: "烫"},
    "yao":  {1: "腰", 2: "摇", 3: "咬", 4: "药"},
    "xi":   {1: "西", 2: "习", 3: "洗", 4: "戏"},
}

VOICES = ["alloy", "nova", "onyx", "shimmer"]

INSTRUCTIONS = (
    "You are a Mandarin Chinese pronunciation teacher. Pronounce the single "
    "Chinese character clearly and slowly in isolation, with its correct "
    "lexical tone, standard Beijing Mandarin. Say only the character, nothing else."
)


def synth_one(client, syllable, tone, hanzi, voice):
    out = AUDIO / f"{syllable}{tone}_{voice}.wav"
    if out.exists() and out.stat().st_size > 1000:
        return str(out), "cached"
    resp = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=hanzi,
        instructions=INSTRUCTIONS,
        response_format="wav",
    )
    out.write_bytes(resp.content)
    return str(out), "ok"


def main():
    load_env()
    import openai

    client = openai.OpenAI()
    jobs = [
        (syl, tone, hanzi, voice)
        for syl, tones in QUADS.items()
        for tone, hanzi in tones.items()
        for voice in VOICES
    ]
    manifest = {}
    failures = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {
            pool.submit(synth_one, client, s, t, h, v): (s, t, h, v)
            for s, t, h, v in jobs
        }
        for fut in as_completed(futs):
            s, t, h, v = futs[fut]
            try:
                path, status = fut.result()
                manifest[pathlib.Path(path).name] = {
                    "syllable": s, "tone": t, "hanzi": h, "voice": v,
                }
            except Exception as e:  # noqa: BLE001
                page_if_billing("openai", e)
                failures.append((s, t, v, repr(e)))
    (HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(f"generated {len(manifest)}/{len(jobs)} clips")
    for f in failures[:5]:
        print("FAIL", f, file=sys.stderr)


if __name__ == "__main__":
    main()
