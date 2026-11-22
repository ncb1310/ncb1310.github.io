"""Refresh public game news, retaining the last good entries on source errors."""
import json
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

JST = timezone(timedelta(hours=9))
CACHE = Path("game-news.json")


def read(url):
    with urlopen(Request(url, headers={"User-Agent": "NCB-News/1.0"}), timeout=20) as response:
        return response.read()


def rss(url, label, domain):
    channel = ElementTree.fromstring(read(url)).find("channel")
    for item in channel.findall("item"):
        title = unescape(item.findtext("title", "")).strip()
        link = item.findtext("link", "").strip()
        if urlsplit(link).hostname != domain or urlsplit(link).scheme != "https":
            continue
        if domain == "www.centurygames.com" and "kingshot" not in (title + link).lower():
            continue
        stamp = parsedate_to_datetime(item.findtext("pubDate")).astimezone(JST)
        yield {"title": label + "｜" + title, "date": stamp.date().isoformat(),
               "source": link, "body": "掲載元：" + label, "image": ""}


def ios():
    app = json.loads(read("https://itunes.apple.com/lookup?id=6739554056&country=jp&lang=ja_jp"))["results"][0]
    if app["trackId"] != 6739554056:
        raise ValueError("unexpected app")
    date = datetime.fromisoformat(app["currentVersionReleaseDate"].replace("Z", "+00:00")).astimezone(JST)
    yield {"title": "iPhone版アップデート｜バージョン " + app["version"],
           "date": date.date().isoformat(), "source": "https://apps.apple.com/jp/app/id6739554056",
           "body": app.get("releaseNotes", "").strip()[:400], "image": ""}


def main():
    existing = json.loads(CACHE.read_text()) if CACHE.exists() else []
    entries = {(x["source"], x["title"]): x for x in existing}
    failures = []
    for name, items in [
        ("App Store", ios()),
        ("公式イベント", rss("https://www.centurygames.com/feed/", "運営のお知らせ", "www.centurygames.com")),
        ("攻略ガイド", rss("https://kingshotwiki.com/category/guides-en/feed/", "公式Wiki攻略", "kingshotwiki.com")),
    ]:
        try:
            for item in list(items):
                entries[(item["source"], item["title"])] = item
        except Exception as exc:
            failures.append(name)
            print(f"{name}: {exc}")
    output = sorted(entries.values(), key=lambda item: item["date"], reverse=True)[:40]
    CACHE.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(f"{len(output)} articles. Unavailable: {failures}")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
