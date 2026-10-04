"""Phone + 4-digit PIN accounts on top of the existing farmers.json / vendors.json.

PINs are stored as salted PBKDF2 hashes. Accounts created before this change have no
phone/PIN; they stay selectable as "demo accounts" so existing data keeps working.
"""

import hashlib
import hmac
import os
import re


def hash_pin(pin, salt=None):
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def check_pin(pin, stored):
    try:
        salt, digest = stored.split("$", 1)
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(hash_pin(pin, salt).split("$", 1)[1], digest)


def valid_phone(phone):
    return bool(re.fullmatch(r"[6-9]\d{9}", (phone or "").strip()))


def valid_pin(pin):
    return bool(re.fullmatch(r"\d{4}", (pin or "").strip()))
