"""Bhashini (Government of India, free) speech-to-text and text-to-speech for all 22 scheduled languages.

Needs a free account:  https://bhashini.gov.in/ulca/user/register  -> My Profile -> Generate API key.
Put them in .streamlit/secrets.toml (or environment variables):

    BHASHINI_USER_ID = "..."
    BHASHINI_ULCA_API_KEY = "..."

Flow (from Bhashini's published API docs):
  1. Pipeline Config call (userID + ulcaApiKey headers) returns, per task and language, a serviceId plus the
     inference endpoint and an inference key.
  2. Pipeline Compute call to that endpoint with the task, serviceId and base64 audio / text.

NOTE: written from the documentation; it has NOT been run against the live service (no credentials were
available when it was built). Every call fails soft (returns None) so the app falls back to Whisper / gTTS.
"""

import base64
import io
import os
import time
import wave

import requests

from krishi.languages import BHASHINI

CONFIG_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
PIPELINE_ID = "643930aa521a4b1ba0f4c41d"  # AI4Bharat pipeline (the MeitY one is 64392f96daac500b55c543cd)
_CACHE = {}
_TTL = 3600


def _secret(name):
    try:
        import streamlit as st
        v = st.secrets.get(name)
        if v:
            return v
    except Exception:
        pass
    return os.environ.get(name)


def configured():
    return bool(_secret("BHASHINI_USER_ID") and _secret("BHASHINI_ULCA_API_KEY"))


def supports(lang_code):
    return configured() and BHASHINI.get(lang_code) is not None


def _pipeline(task, lang, timeout=20):
    """Service id + inference endpoint/key for a task and language (cached for an hour)."""
    key = (task, lang)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    r = requests.post(
        CONFIG_URL,
        headers={"userID": _secret("BHASHINI_USER_ID"), "ulcaApiKey": _secret("BHASHINI_ULCA_API_KEY"),
                 "Content-Type": "application/json"},
        json={"pipelineTasks": [{"taskType": task, "config": {"language": {"sourceLanguage": lang}}}],
              "pipelineRequestConfig": {"pipelineId": PIPELINE_ID}},
        timeout=timeout)
    r.raise_for_status()
    d = r.json()
    cfg = next(x for x in d["pipelineResponseConfig"] if x["taskType"] == task)["config"][0]
    ep = d["pipelineInferenceAPIEndPoint"]
    info = {"serviceId": cfg["serviceId"], "url": ep["callbackUrl"],
            "auth": (ep["inferenceApiKey"]["name"], ep["inferenceApiKey"]["value"])}
    _CACHE[key] = (time.time(), info)
    return info


def _wav_rate(audio):
    try:
        with wave.open(io.BytesIO(audio)) as w:
            return w.getframerate()
    except Exception:
        return 16000


def asr(audio_wav, lang_code, timeout=60):
    """Speech (WAV bytes) -> text, or None."""
    lang = BHASHINI.get(lang_code)
    if not (lang and configured()):
        return None
    try:
        p = _pipeline("asr", lang)
        r = requests.post(
            p["url"], headers={p["auth"][0]: p["auth"][1], "Content-Type": "application/json"}, timeout=timeout,
            json={"pipelineTasks": [{"taskType": "asr", "config": {
                      "language": {"sourceLanguage": lang}, "serviceId": p["serviceId"],
                      "audioFormat": "wav", "samplingRate": _wav_rate(audio_wav)}}],
                  "inputData": {"input": [{"source": None}],
                                "audio": [{"audioContent": base64.b64encode(audio_wav).decode()}]}})
        r.raise_for_status()
        text = r.json()["pipelineResponse"][0]["output"][0]["source"]
        return (text or "").strip() or None
    except Exception:
        _CACHE.pop(("asr", lang), None)
        return None


def tts(text, lang_code, gender="female", timeout=60):
    """Text -> WAV bytes, or None."""
    lang = BHASHINI.get(lang_code)
    if not (lang and configured() and text.strip()):
        return None
    try:
        p = _pipeline("tts", lang)
        r = requests.post(
            p["url"], headers={p["auth"][0]: p["auth"][1], "Content-Type": "application/json"}, timeout=timeout,
            json={"pipelineTasks": [{"taskType": "tts", "config": {
                      "language": {"sourceLanguage": lang}, "serviceId": p["serviceId"], "gender": gender}}],
                  "inputData": {"input": [{"source": text}], "audio": [{"audioContent": None}]}})
        r.raise_for_status()
        audio = r.json()["pipelineResponse"][0]["audio"][0]["audioContent"]
        return base64.b64decode(audio) if audio else None
    except Exception:
        _CACHE.pop(("tts", lang), None)
        return None
