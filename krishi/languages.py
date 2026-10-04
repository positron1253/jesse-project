"""Languages the app can talk in, and which provider covers each part (typed text, speech in, speech out).

code        canonical code = Google Translate code (used for translation and stored in chats)
bhashini    ISO-639 code Bhashini expects for ASR/TTS (None = not offered)
whisper     speech-to-text via Whisper on Together: True only where we TESTED it (Hindi, Marathi, Bengali, Telugu,
            Tamil, Gujarati, Kannada, Malayalam, Punjabi, Urdu, Nepali, English)
gtts        text-to-speech via Google's free gTTS voices (11 Indian languages + English)
Bodo and Kashmiri are left out because Google Translate cannot translate them yet.
Everything beyond Whisper/gTTS needs a free Bhashini account (see krishi/bhashini.py).
"""

# name, native name, code, bhashini code, whisper tested, gTTS voice
_ROWS = [
    ("Hindi", "हिन्दी", "hi", "hi", True, True),
    ("Marathi", "मराठी", "mr", "mr", True, True),
    ("Bengali", "বাংলা", "bn", "bn", True, True),
    ("Telugu", "తెలుగు", "te", "te", True, True),
    ("Tamil", "தமிழ்", "ta", "ta", True, True),
    ("Gujarati", "ગુજરાતી", "gu", "gu", True, True),
    ("Kannada", "ಕನ್ನಡ", "kn", "kn", True, True),
    ("Malayalam", "മലയാളം", "ml", "ml", True, True),
    ("Punjabi", "ਪੰਜਾਬੀ", "pa", "pa", True, True),
    ("Urdu", "اردو", "ur", "ur", True, True),
    ("Odia", "ଓଡ଼ିଆ", "or", "or", False, False),
    ("Assamese", "অসমীয়া", "as", "as", False, False),
    ("Nepali", "नेपाली", "ne", "ne", True, True),
    ("Sanskrit", "संस्कृतम्", "sa", "sa", False, False),
    ("Sindhi", "سنڌي", "sd", "sd", False, False),
    ("Konkani", "कोंकणी", "gom", "kok", False, False),
    ("Maithili", "मैथिली", "mai", "mai", False, False),
    ("Dogri", "डोगरी", "doi", "doi", False, False),
    ("Manipuri (Meitei)", "মৈতৈলোন্", "mni-Mtei", "mni", False, False),
    ("Santali", "ᱥᱟᱱᱛᱟᱲᱤ", "sat", "sat", False, False),
    ("English", "English", "en", "en", True, True),
]

LANGUAGES = {name: code for name, native, code, *_ in _ROWS}          # name -> canonical code
NATIVE = {code: native for name, native, code, *_ in _ROWS}
NAME = {code: name for name, native, code, *_ in _ROWS}
BHASHINI = {code: b for _, _, code, b, *_ in _ROWS}
WHISPER = {code for _, _, code, _, w, _ in _ROWS if w}
GTTS = {code for _, _, code, _, _, g in _ROWS if g}


def label(code):
    return f"{NAME[code]} · {NATIVE[code]}" if NAME[code] != NATIVE[code] else NAME[code]
