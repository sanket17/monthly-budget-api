#!/usr/bin/env python
"""
Regenerate docs/api/openapi.yaml and the Postman collection/environments.

    python scripts/build_api_docs.py          # write the files
    python scripts/build_api_docs.py --check  # exit 1 if they are out of date

Run it after changing any endpoint, serializer, or config/api_docs.py. The test
suite fails when the committed files are stale, so CI catches a forgotten run.
Needs the usual env (SECRET_KEY, DATABASE_URL) but never touches the database.
"""

import difflib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django  # noqa: E402

django.setup()

from config.docs_build import DOCS_DIR, build_all  # noqa: E402


def main(check):
    stale = []
    for relative, text in build_all().items():
        target = DOCS_DIR / relative
        current = target.read_text() if target.exists() else None
        if current == text:
            continue
        stale.append(relative)
        if check:
            diff = difflib.unified_diff(
                (current or "").splitlines(),
                text.splitlines(),
                "committed",
                "generated",
                lineterm="",
                n=1,
            )
            print("\n".join(list(diff)[:30]))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
            print(f"wrote {target.relative_to(ROOT)}")
    if check and stale:
        print(
            f"out of date: {', '.join(stale)} - run: python scripts/build_api_docs.py"
        )
        return 1
    if not stale:
        print("api docs already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
