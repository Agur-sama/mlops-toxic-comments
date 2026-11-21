from __future__ import annotations

import nltk

if __name__ == "__main__":
    for resource in ("stopwords", "wordnet", "omw-1.4"):
        nltk.download(resource, raise_on_error=True)

