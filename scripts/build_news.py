#!/usr/bin/env python3
"""Build a static JSON news feed from Pages CMS Markdown files."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
items = []
for file in sorted((root / "news").glob("*.md")):
    content = file.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", content, re.S)
    if not match:
        continue
    front, body = match.groups()
    fields = {}
    for line in front.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip('"').strip("'")
    if not fields.get("title"):
        continue
    items.append({
        "title": fields["title"],
        "date": fields.get("date", ""),
        "source": fields.get("source", ""),
        "image": fields.get("image", ""),
        "body": body.strip()[:3000],
    })
cache = root / "game-news.json"
if cache.exists():
    items.extend(json.loads(cache.read_text()))
items.sort(key=lambda x: x["date"], reverse=True)
(root / "news.json").write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Built news.json with {len(items)} article(s)")
