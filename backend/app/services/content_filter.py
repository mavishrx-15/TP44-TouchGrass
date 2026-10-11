"""Conservative community text filter, applied on writes and public reads.

This word filter is not a toxicity model. Human approval is still required.
NFKC and removal of invisible characters catch common trivial evasions.
"""

import re
import unicodedata

_WORDS = re.compile(
    r"\b(?:fuck\w*|motherfuck\w*|shit|bullshit|bitch\w*|cunt\w*|"
    r"nigg(?:er|a)\w*|faggot\w*|porn\w*|hentai)\b",
    re.IGNORECASE,
)
_PHRASES = ("kill yourself", "kys", "去死", "操你", "傻逼", "色情", "约炮")


def is_unsafe_text(body: str) -> bool:
    normalized = unicodedata.normalize("NFKC", body).casefold()
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Cf")
    normalized = normalized.translate(
        str.maketrans({"@": "a", "0": "o", "1": "i", "3": "e", "$": "s"})
    )
    return bool(_WORDS.search(normalized)) or any(phrase in normalized for phrase in _PHRASES)
