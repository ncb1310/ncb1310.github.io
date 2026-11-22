"""Collect publicly listed candidates. No player data or redemption requests."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException

SOURCES = {
    "wiki": "https://kingshotwiki.com/giftcodes/",
    "en": "https://kingshot.net/gift-codes/redeem",
    "zh": "https://kingshot.net/zh-CN/gift-codes/redeem",
}
CODE = re.compile(r"[A-Za-z0-9_-]{3,64}")
LEDGER = Path("gift-codes/candidates.json")


def extract(html, source):
    soup = BeautifulSoup(html, "html.parser")
    codes = set()
    if source == "wiki":
        for button in soup.find_all(["button", "a", "span"]):
            if button.get_text(strip=True).lower() != "copy":
                continue
            item = button.find_parent("li") or button.parent
            text = re.sub(r"\s*copy\s*$", "", item.get_text(" ", strip=True), flags=re.I)
            if CODE.fullmatch(text):
                codes.add(text)
    else:
        for checkbox in soup.select('input[type="checkbox"]'):
            item = checkbox.find_parent("li") or checkbox.find_parent("label")
            if item:
                first = next(iter(item.stripped_strings), "")
                token = re.split(r"\s|新|未公布|\d+天后过期", first, maxsplit=1)[0]
                if CODE.fullmatch(token):
                    codes.add(token)
    if not codes:
        raise ValueError("No recognizable code list")
    return codes


def rendered_codes(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    with webdriver.Chrome(options=options) as driver:
        driver.set_page_load_timeout(30)
        driver.get(url)

        def read_list(browser):
            soup = BeautifulSoup(browser.page_source, "html.parser")
            heading = soup.find(lambda tag: tag.name in ("h2", "h3") and
                                tag.get_text(strip=True).lower() in ("gift codes", "兑换码"))
            if not heading:
                return False
            listing = heading.find_next(["ul", "ol"])
            if not listing:
                return False
            result = set()
            for row in listing.find_all("li"):
                if not row.find("input"):
                    continue
                token = next(iter(row.stripped_strings), "").split()[0:1]
                if token and CODE.fullmatch(token[0]):
                    result.add(token[0])
            return result or False

        return WebDriverWait(driver, 15).until(read_list)


def main():
    now = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
    state = json.loads(LEDGER.read_text())
    checks = {}
    for source, url in SOURCES.items():
        try:
            request = Request(url, headers={"User-Agent": "NCB-GiftCode-Watcher/1.0"})
            with urlopen(request, timeout=30) as response:
                html = response.read()
            try:
                codes = extract(html, source)
            except ValueError:
                if source == "wiki":
                    raise
                codes = rendered_codes(url)
            for code in sorted(codes):
                entry = state["candidates"].setdefault(code, {
                    "first_seen_jst": now, "released_at": None, "sources": []})
                if url not in entry["sources"]:
                    entry["sources"].append(url)
            checks[url] = {"status": "ok", "count": len(codes)}
        except (OSError, ValueError, WebDriverException) as exc:
            checks[url] = {"status": "unavailable", "reason": str(exc).split("Stacktrace:")[0][:200]}
    state.update(checked_at_jst=now, checks=checks)
    LEDGER.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(checks, ensure_ascii=False))
    return int(any(check["status"] != "ok" for check in checks.values()))


if __name__ == "__main__":
    raise SystemExit(main())
