from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".js", ".css", ".html", ".md", ".toml", ".txt", ".json", ".yml", ".yaml"}
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules"}


def looks_like_emoji(codepoint: int) -> bool:
    ranges = [
        (0x1F000, 0x1FAFF),
        (0x2600, 0x27BF),
        (0x2300, 0x23FF),
        (0xFE00, 0xFE0F),
        (0x1F1E6, 0x1F1FF),
    ]
    return any(start <= codepoint <= end for start, end in ranges)


def main() -> int:
    findings = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for index, char in enumerate(text):
            if looks_like_emoji(ord(char)):
                findings.append((path.relative_to(ROOT), index, f"U+{ord(char):04X}"))
    if findings:
        for item in findings:
            print(*item)
        return 1
    print("No emoji-range Unicode characters found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
