"""'Ask' screen: talk to Krishi Sahay by voice or text in your own language; chat is saved per account."""

import streamlit as st

from krishi import assistant
from krishi import bhashini
from krishi.languages import LANGUAGES, NAME, label
from krishi.i18n import GUIDE_LANGUAGE, current_lang, t


@st.cache_data(show_spinner=False, max_entries=200)
def _voice(text, lang_code):
    try:
        return assistant.speak(text, lang_code)
    except Exception:
        return None


def _history(user):
    key = f"chat_{user['id']}"
    if key not in st.session_state:
        st.session_state[key] = assistant.load_history(user["id"])
    return st.session_state[key]


def _turn(user, api_key, lang_code, text=None, audio=None):
    history = _history(user)
    try:
        with st.spinner(t("ask.thinking")):
            if audio is not None:
                try:
                    text = assistant.transcribe(audio, lang_code, api_key)
                except assistant.NoVoiceInput:
                    st.warning(t("ask.cap_no_mic"))
                    return False
            if not text or not text.strip():
                st.warning(t("ask.empty"))
                return False
            text = text.strip()
            q_en = text if lang_code == "en" else assistant.translate(text, "en", lang_code)
            reply, reply_en, audio_out = assistant.respond(user, history, text, q_en, lang_code, api_key)
    except Exception:
        st.error(t("ask.error"))
        return False

    new = [assistant.make_msg("user", text, q_en, lang_code), assistant.make_msg("assistant", reply, reply_en, lang_code)]
    assistant.append_messages(user["id"], new)
    history.extend(new)
    if audio_out:
        st.session_state["ask_autoplay"] = {"id": new[1]["id"], "audio": audio_out}
    return True


def render(user, api_key):
    st.subheader(t("ask.title"))
    st.caption(t("ask.sub"))

    codes = list(LANGUAGES.values())
    default = LANGUAGES[GUIDE_LANGUAGE[current_lang()]]
    lang_code = st.selectbox(t("ask.lang"), codes, index=codes.index(default), format_func=label, key="ask_lang")
    can_listen, can_speak = assistant.has_stt(lang_code), assistant.has_tts(lang_code)
    if not (can_listen and can_speak):
        missing = []
        if not can_listen:
            missing.append(t("ask.cap_no_mic"))
        if not can_speak:
            missing.append(t("ask.cap_no_voice"))
        st.info(" ".join(missing) + ("" if bhashini.configured() else " " + t("ask.cap_bhashini")))

    history = _history(user)
    autoplay = st.session_state.pop("ask_autoplay", None)

    # --- conversation ---
    box = st.container()
    with box:
        if not history:
            with st.chat_message("assistant"):
                st.write(t("ask.welcome"))
        for m in history:
            with st.chat_message(m["role"]):
                st.write(m["text"])
                if m["role"] != "assistant":
                    continue
                if autoplay and autoplay["id"] == m["id"]:
                    st.audio(autoplay["audio"], format=assistant.audio_mime(autoplay["audio"]), autoplay=True)
                elif assistant.has_tts(m["lang"]):
                    if st.button(t("ask.listen"), key=f"say_{m['id']}"):
                        audio = _voice(m["text"], m["lang"])
                        if audio:
                            st.audio(audio, format=assistant.audio_mime(audio), autoplay=True)
                if m["lang"] != "en" and m.get("text_en"):
                    with st.expander(t("ask.english")):
                        st.write(m["text_en"])
        if history and not assistant.has_tts(history[-1]["lang"]):
            st.caption(t("ask.no_audio"))

    # --- input: microphone first, typing as a fallback ---
    n = st.session_state.get("ask_mic_n", 0)
    recording = st.audio_input(t("ask.mic"), key=f"ask_mic_{n}") if can_listen else None
    typed = st.chat_input(t("ask.type"))

    if recording is not None:
        if _turn(user, api_key, lang_code, audio=recording.getvalue()):
            st.session_state["ask_mic_n"] = n + 1  # fresh recorder so the same clip is not sent twice
            st.rerun()
        else:
            st.session_state["ask_mic_n"] = n + 1
    elif typed:
        if _turn(user, api_key, lang_code, text=typed):
            st.rerun()

    st.caption(t("ask.kvk"))
    st.caption("🔒 " + t("ask.privacy"))
    if history and st.button(t("ask.clear"), key="ask_clear"):
        assistant.clear_history(user["id"])
        st.session_state[f"chat_{user['id']}"] = []
        st.rerun()
