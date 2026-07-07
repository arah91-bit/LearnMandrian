"""Second opinion: Gemini (native audio) identifies the tone of every clip.

Arbitrates TTS-label vs classifier disagreements: if Gemini also hears
something other than the intended tone, the TTS clip itself is suspect.
"""
import base64
import json
import os
import pathlib
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from api_alerts import page_if_billing
PROVIDERS = {
    "gemini": ("gemini-3.5-flash",
               "https://generativelanguage.googleapis.com/v1beta/openai/",
               "GEMINI_API_KEY"),
    "gpt": ("gpt-audio-1.5", None, "OPENAI_API_KEY"),
}

PROMPT = (
    "You will hear one isolated Mandarin Chinese syllable. Identify its "
    "lexical tone. Answer with a single digit only: 1 (high level), "
    "2 (rising), 3 (low/dipping), 4 (falling), or 5 (neutral). "
    "If the audio is not a clean single Mandarin syllable, answer 0."
)


def load_env():
    path = pathlib.Path(os.environ.get("ENV_FILE", ".env"))
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ[k.strip()] = v.strip()


def judge(client, model, fname):
    b64 = base64.b64encode((HERE / "audio" / fname).read_bytes()).decode()
    resp = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "input_audio",
                 "input_audio": {"data": b64, "format": "wav"}},
            ],
        }],
        modalities=["text"],
        max_tokens=2000,
    )
    text = resp.choices[0].message.content or ""
    m = re.search(r"[0-5]", text)
    if not m:
        print(f"    unparsed({fname}): {text[:120]!r}", file=sys.stderr)
    return int(m.group()) if m else -1


def main():
    load_env()
    import openai

    provider = sys.argv[1] if len(sys.argv) > 1 else "gpt"
    model, base, key_env = PROVIDERS[provider]
    client = openai.OpenAI(api_key=os.environ[key_env], base_url=base)
    manifest = json.loads((HERE / "manifest.json").read_text())
    verdicts = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(judge, client, model, f): f for f in sorted(manifest)}
        for fut in as_completed(futs):
            f = futs[fut]
            try:
                verdicts[f] = fut.result()
            except Exception as e:  # noqa: BLE001
                page_if_billing(provider, e)
                print("FAIL", f, repr(e)[:200], file=sys.stderr)
    (HERE / "gemini_verdicts.json").write_text(json.dumps(verdicts, indent=1))
    ok = {f: v for f, v in verdicts.items() if v in (1, 2, 3, 4)}
    agree = sum(1 for f, v in ok.items() if v == manifest[f]["tone"])
    print(f"judged {len(verdicts)} clips; usable verdicts {len(ok)}")
    print(f"Gemini agrees with TTS label: {agree}/{len(ok)} = {agree/len(ok):.1%}")
    for f, v in sorted(verdicts.items()):
        t = manifest[f]["tone"]
        if v != t:
            print(f"  disagree: {f} label={t} gemini={v}")


if __name__ == "__main__":
    main()
