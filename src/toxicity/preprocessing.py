from __future__ import annotations

import html
import re
from functools import lru_cache

URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?|\d+|[^\w\s]", re.IGNORECASE)


def minimal_clean(text: str) -> str:
    return SPACE_RE.sub(" ", str(text).replace("\x00", " ")).strip()


def standard_clean(text: str) -> str:
    value = html.unescape(str(text))
    value = TAG_RE.sub(" ", value)
    value = URL_RE.sub(" URL ", value)
    value = minimal_clean(value).lower()
    return " ".join(TOKEN_RE.findall(value))


@lru_cache(maxsize=1)
def _nltk_resources():
    try:
        from nltk.corpus import stopwords, wordnet
        from nltk.stem import WordNetLemmatizer

        stop = set(stopwords.words("english"))
        # Preserve negation: it can reverse the meaning of abusive phrases.
        stop.difference_update({"no", "not", "nor", "never"})
        _ = wordnet.synsets("test")
        return stop, WordNetLemmatizer()
    except LookupError as exc:
        raise RuntimeError(
            "NLTK corpora are missing. Run `python scripts/download_nltk.py`."
        ) from exc


def extended_clean(text: str) -> str:
    stop, lemmatizer = _nltk_resources()
    tokens = standard_clean(text).split()
    processed = [
        lemmatizer.lemmatize(token)
        for token in tokens
        if token not in stop and (token.isalpha() or token in {"!", "?"})
    ]
    return " ".join(processed)


PREPROCESSORS = {
    "minimal": minimal_clean,
    "standard": standard_clean,
    "extended": extended_clean,
}


def get_preprocessor(name: str):
    try:
        return PREPROCESSORS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown preprocessing variant: {name}") from exc
