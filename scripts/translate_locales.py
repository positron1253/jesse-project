"""Machine-translate krishi/locales/en.json into hi.json and mr.json.

Placeholders like {crop} and emoji are protected. Re-run after adding English keys;
existing translations are kept unless --force is given. Review output with a native speaker.

    py -3.11 scripts/translate_locales.py [--force]
"""

import json
import os
import re
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOC = os.path.join(ROOT, "krishi", "locales")
KEEP_ENGLISH = {"app.name"}


def translate(text, lang):
    # Protect {placeholders} with tokens the translator leaves alone
    names = re.findall(r"\{(\w+)\}", text)
    protected = text
    for i, n in enumerate(names):
        protected = protected.replace("{" + n + "}", f"[[{i}]]", 1)
    for attempt in range(6):  # the free endpoint rate-limits (HTTP 429); back off and retry
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": lang, "dt": "t", "q": protected},
            timeout=20,
        )
        if r.status_code != 429:
            break
        time.sleep(3 * (attempt + 1))
    r.raise_for_status()
    out = "".join(p[0] for p in r.json()[0] if p[0])
    for i, n in enumerate(names):
        out = re.sub(r"\[\[\s*" + str(i) + r"\s*\]\]", "{" + n + "}", out)
    return out


def main(force=False):
    with open(os.path.join(LOC, "en.json"), encoding="utf-8") as f:
        en = json.load(f)
    for lang in ("hi", "mr"):
        path = os.path.join(LOC, f"{lang}.json")
        existing = {}
        if os.path.exists(path) and not force:
            with open(path, encoding="utf-8") as f:
                existing = json.load(f)
        out = {}
        for k, v in en.items():
            if k in existing:
                out[k] = existing[k]
            elif k in KEEP_ENGLISH:
                out[k] = v
            else:
                out[k] = translate(v, lang)
                time.sleep(0.15)
            if set(re.findall(r"\{\w+\}", v)) != set(re.findall(r"\{\w+\}", out[k])):
                print(f"[{lang}] placeholder mismatch for {k}: {out[k]!r} — keeping English")
                out[k] = v
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(lang, len(out), "strings")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
