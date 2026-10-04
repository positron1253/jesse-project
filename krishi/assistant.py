"""Voice chat assistant: speak in your language -> text -> contextual answer -> spoken reply.

Pipeline for one turn
  1. Speech-to-text: Bhashini (all 22 languages, free account) -> Google Cloud (optional key) -> Together
     `openai/whisper-large-v3` (12 tested languages, works with the existing key)
  2. Native text -> English (Google Translate public endpoint, same as the audio guide)
  3. Llama-3.3-70B on Together answers in English, given the farmer's context + last turns of the chat
  4. English reply -> farmer's language (Google Translate) -> gTTS audio
Chats are stored per account in chats.json (text only, no audio files).
"""

import json
import os
import re
import time
import uuid
from datetime import datetime
from io import BytesIO

import requests
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(__file__))
CHATS_FILE = os.path.join(ROOT, "chats.json")
MAX_STORED = 300       # messages kept per account
HISTORY_TURNS = 14     # most recent messages sent to the model

CHAT_MODELS = [
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
]
STT_MODEL = "openai/whisper-large-v3"
from krishi import bhashini
from krishi.languages import GTTS, WHISPER


class NoVoiceInput(Exception):
    """No speech-to-text provider is available for this language."""


def has_stt(lang_code):
    return bhashini.supports(lang_code) or (bool(google_stt_key()) and lang_code in GOOGLE_STT_CODES) \
        or lang_code in WHISPER


def has_tts(lang_code):
    return lang_code in GTTS or bhashini.supports(lang_code)


def audio_mime(audio):
    return "audio/wav" if audio[:4] == b"RIFF" else "audio/mp3"

SYSTEM_PROMPT = """You are Krishi Sahay, a friendly, practical farming assistant for smallholder farmers in India.
Talk like a trusted, experienced neighbour. Rules:
- Answer in simple English using short sentences. A translator will convert it to the farmer's language, so avoid idioms, slang and abbreviations.
- Keep answers under 110 words unless the farmer asks for detail. Plain text only: no markdown, no bullet symbols, no asterisks, no tables. Use numbered sentences like "First, ... Second, ..." if you need steps.
- Use rupees, acres, quintals. Never invent prices, MSP, yields, scheme rules or weather. Use only the numbers in FARMER CONTEXT. If you do not have a number, say so and suggest checking the Farm Plan screen or the local mandi.
- For plant diseases, pests and pesticide use: give only general, safe guidance, never exact doses of poisons, and tell the farmer to confirm with the local Krishi Vigyan Kendra (KVK) or the Kisan Call Centre 1800-180-1551.
- If the question is not about farming, water, markets or farm life, politely bring the conversation back to farming.
- Be honest about uncertainty. Never promise a profit. Remember what the farmer said earlier in this chat.

FARMER CONTEXT (may be incomplete):
{context}
"""


# ---------------- storage ----------------
def _load():
    if os.path.exists(CHATS_FILE):
        try:
            with open(CHATS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save(data):
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def load_history(user_id):
    return _load().get(user_id, [])


def append_messages(user_id, msgs):
    data = _load()
    hist = data.setdefault(user_id, [])
    hist.extend(msgs)
    data[user_id] = hist[-MAX_STORED:]
    _save(data)


def clear_history(user_id):
    data = _load()
    data.pop(user_id, None)
    _save(data)


def make_msg(role, text, text_en, lang):
    return {"id": str(uuid.uuid4()), "role": role, "text": text, "text_en": text_en, "lang": lang,
            "ts": datetime.now().isoformat(timespec="seconds")}


# ---------------- context ----------------
def build_context(user):
    """Facts about this farmer taken from their account, current Farm Plan session and saved plans."""
    from krishi import plans as plans_mod
    from krishi.crop_table import crop_names

    lines = [f"Name: {user.get('name')}", f"Today: {datetime.now().date().isoformat()}"]
    focus = st.session_state.get("ask_focus")
    if focus:
        from krishi.crop_table import crop_names as _cn
        line = f"The farmer is asking about THEIR crop {_cn(focus['crop_id'])['en']} on {focus.get('acres', 0):g} acre ({focus.get('water')} water)"
        if focus.get("sow_date"):
            try:
                sown = datetime.fromisoformat(focus["sow_date"]).date()
                days = (datetime.now().date() - sown).days
                line += f", sowing date {sown.isoformat()} ({'day ' + str(days) + ' after sowing' if days >= 0 else str(-days) + ' days before sowing'})"
            except Exception:
                pass
        lines.append(line + ". Answer about this crop unless they ask about something else.")
    farm = st.session_state.get("farm") or {}
    place = ", ".join(x for x in [farm.get("place") or "", farm.get("district") or user.get("district") or "",
                                  farm.get("state") or user.get("state") or ""] if x)
    if place:
        lines.append(f"Farm location: {place}")
    if farm.get("acres_w") is not None:
        lines.append(f"Land: {farm.get('acres_w', 0):g} acre with water ({farm.get('water')}), "
                     f"{farm.get('acres_r', 0):g} acre rain-only. Soil pH about {farm.get('ph')}.")
    from krishi import soilcard
    described = soilcard.describe(farm.get("soil_card"))
    if described:
        lines.append("Soil test values (ratings are approximate): " + described + ".")
    if farm.get("soil"):
        lines.append(f"Soil type: {farm['soil']}.")
    clim = farm.get("climate")
    if clim and farm.get("season"):
        lines.append(f"Local climate for {farm['season']} season: about {clim.get('temperature')} C average, "
                     f"{clim.get('rainfall')} mm rain per month.")

    options = farm.get("options") or {}
    for plot, opts in options.items():
        for o in opts[:3]:
            name = crop_names(o.crop_id)["en"]
            lo, hi = o.profit_normal
            lines.append(
                f"Option on {plot} land: {name}, usual-year profit about Rs {lo:,.0f} to {hi:,.0f} per acre, "
                f"bad-year result Rs {(o.profit_worst or 0.0):,.0f} per acre, risk {o.risk}"
                f"{', MSP Rs ' + format(o.msp, ',.0f') + ' per quintal' if o.msp else ''}.")

    try:
        for season in ("Kharif", "Rabi", "Zaid"):
            saved = plans_mod.farmer_plan(user["id"], season)
            if saved:
                parts = [f"{crop_names(p['crop_id'])['en']} {p['acres']:g} acre ({p['plot']} land)" for p in saved]
                lines.append(f"Saved plan for {season}: " + "; ".join(parts))
    except Exception:
        pass

    nearby = farm.get("nearby")
    if nearby:
        for crop_id, buyers in list(nearby.buyers.items())[:4]:
            for b in buyers[:2]:
                price = b.get("price_per_quintal")
                lines.append(
                    f"Buyer near farm: {b['vendor_name']}, {b['distance_km']} km, wants {round(b['open_q'])} quintal "
                    f"{crop_names(crop_id)['en']}" + (f" at Rs {price:,.0f} per quintal" if price else ""))
    if len(lines) <= 2:
        lines.append("No Farm Plan has been made yet. If the farmer asks what to grow, suggest the Farm Plan screen.")
    return "\n".join(lines)


# ---------------- speech / language ----------------
GOOGLE_STT_CODES = {
    "hi": "hi-IN", "mr": "mr-IN", "bn": "bn-IN", "te": "te-IN", "ta": "ta-IN", "ur": "ur-IN", "gu": "gu-IN",
    "kn": "kn-IN", "ml": "ml-IN", "pa": "pa-Guru-IN", "or": "or-IN", "en": "en-IN",
}


def google_stt_key():
    """Optional Google Cloud Speech-to-Text key (st.secrets or env GOOGLE_STT_API_KEY)."""
    try:
        key = st.secrets.get("GOOGLE_STT_API_KEY")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("GOOGLE_STT_API_KEY")


def _transcribe_google(audio_bytes, lang_code, key, timeout=60):
    import base64
    r = requests.post(
        "https://speech.googleapis.com/v1/speech:recognize", params={"key": key}, timeout=timeout,
        json={"config": {"languageCode": GOOGLE_STT_CODES.get(lang_code, "hi-IN"), "enableAutomaticPunctuation": True},
              "audio": {"content": base64.b64encode(audio_bytes).decode()}})
    r.raise_for_status()
    results = r.json().get("results", [])
    return " ".join(x["alternatives"][0]["transcript"] for x in results if x.get("alternatives")).strip()


def _transcribe_whisper(audio_bytes, lang_code, api_key, timeout=90):
    data = {"model": STT_MODEL, "language": lang_code}
    r = requests.post("https://api.together.xyz/v1/audio/transcriptions",
                      headers={"Authorization": f"Bearer {api_key}"},
                      files={"file": ("speech.wav", audio_bytes, "audio/wav")}, data=data, timeout=timeout)
    r.raise_for_status()
    return (r.json().get("text") or "").strip()


def transcribe(audio_bytes, lang_code, api_key):
    """Speech -> text. Order: Bhashini (all 22 languages, if configured) -> Google Cloud (if key) -> Whisper."""
    if bhashini.supports(lang_code):
        text = bhashini.asr(audio_bytes, lang_code)
        if text:
            return text
    gkey = google_stt_key()
    if gkey and lang_code in GOOGLE_STT_CODES:
        try:
            text = _transcribe_google(audio_bytes, lang_code, gkey)
            if text:
                return text
        except Exception:
            pass
    if lang_code in WHISPER:
        return _transcribe_whisper(audio_bytes, lang_code, api_key)
    raise NoVoiceInput(lang_code)


def translate(text, target, source="auto", chunk_size=1500, timeout=20):
    """Google Translate public endpoint; the `googletrans` package is broken with current httpx."""
    if not text.strip() or target == source:
        return text

    def one(chunk):
        for attempt in range(3):  # the free endpoint rate-limits (HTTP 429); back off briefly
            r = requests.get("https://translate.googleapis.com/translate_a/single",
                             params={"client": "gtx", "sl": source, "tl": target, "dt": "t", "q": chunk}, timeout=timeout)
            if r.status_code != 429:
                break
            time.sleep(1.5 * (attempt + 1))
        r.raise_for_status()
        return "".join(p[0] for p in r.json()[0] if p[0])

    chunks, cur = [], ""
    for para in text.split("\n"):
        if len(cur) + len(para) + 1 > chunk_size and cur:
            chunks.append(cur)
            cur = ""
        cur += para + "\n"
    if cur.strip():
        chunks.append(cur)
    return "\n".join(one(c) for c in chunks if c.strip()).strip()


def speak(text, lang_code):
    """Audio bytes (mp3 or wav), or None if no voice exists for the language."""
    if not text.strip():
        return None
    if lang_code in GTTS:
        from gtts import gTTS
        buf = BytesIO()
        gTTS(text=text, lang=lang_code).write_to_fp(buf)
        return buf.getvalue()
    if bhashini.supports(lang_code):
        return bhashini.tts(text, lang_code)
    return None


# ---------------- the model ----------------
def _clean(text):
    text = re.sub(r"[*#`_>]+", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def answer(history, question_en, context, api_key):
    """history: stored messages (oldest first). Returns the English answer."""
    from together import Together

    msgs = [{"role": "system", "content": SYSTEM_PROMPT.format(context=context)}]
    for m in history[-HISTORY_TURNS:]:
        msgs.append({"role": m["role"], "content": m.get("text_en") or m["text"]})
    msgs.append({"role": "user", "content": question_en})

    client = Together(api_key=api_key)
    last = None
    for model in CHAT_MODELS:
        try:
            resp = client.chat.completions.create(model=model, messages=msgs, max_tokens=420, temperature=0.4)
            text = resp.choices[0].message.content if resp.choices else ""
            if text:
                return _clean(text)
        except Exception as e:  # model retired / rate limited -> try the next
            last = e
    raise RuntimeError(f"No chat model available ({last})")


def respond(user, history, question_native, question_en, lang_code, api_key):
    """Run model + translation + voice. Returns (reply_native, reply_en, audio_bytes_or_None, reply_lang).

    If translation is unavailable (rate-limited), the reply comes back in English with English voice, reply_lang='en'.
    """
    reply_en = answer(history, question_en, build_context(user), api_key)
    reply_lang = lang_code
    if lang_code == "en":
        reply_native = reply_en
    else:
        try:
            reply_native = translate(reply_en, lang_code, "en")
        except Exception:
            reply_native, reply_lang = reply_en, "en"
    try:
        audio = speak(reply_native, reply_lang)
    except Exception:
        audio = None
    return reply_native, reply_en, audio, reply_lang
