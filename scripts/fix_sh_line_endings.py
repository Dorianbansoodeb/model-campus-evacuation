#!/usr/bin/env python3
"""Rewrite shell scripts with Unix LF line endings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in sorted(ROOT.glob("*.sh")):
    text = path.read_text(encoding="utf-8")
    fixed = text.replace("\r\n", "\n").replace("\r", "\n")
    path.write_text(fixed, encoding="utf-8", newline="\n")
    print(f"fixed {path.name}")
