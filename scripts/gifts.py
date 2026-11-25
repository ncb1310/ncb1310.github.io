"""Local registration service. Run with python3 scripts/gifts.py."""
import os
import json
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "gifts/index.html"
DATABASE = Path.home() / ".ncb-gifts.sqlite3"


BOT_DB = os.environ.get("NCB_BOT_DB")
GROUP = os.environ.get("NCB_GIFT_GROUP")


def bot_db(name, mode):
    path = Path(BOT_DB, name + ".sqlite").resolve()
    return sqlite3.connect(path.as_uri() + "?mode=" + mode, uri=True)


def check_group():
    with bot_db("alliance", "ro") as db:
        if not db.execute("SELECT 1 FROM alliance_list WHERE alliance_id=?", (GROUP,)).fetchone():
            raise ValueError("Unknown gift group")
    with bot_db("giftcode", "ro") as db:
        if not db.execute("SELECT 1 FROM giftcodecontrol WHERE alliance_id=? AND status=1", (GROUP,)).fetchone():
            raise ValueError("Enable auto-redemption for the gift group first")


def register(player, kingdom):
    if BOT_DB:
        check_group()
        with bot_db("users", "rw") as db:
            db.execute("INSERT INTO users(fid, kid, alliance, nickname) VALUES(?,?,?,?) "
                       "ON CONFLICT(fid) DO NOTHING", (player, kingdom, GROUP, player))
            existing = db.execute("SELECT kid, alliance FROM users WHERE fid=?", (player,)).fetchone()
            return existing == (int(kingdom), str(GROUP))
    with sqlite3.connect(DATABASE) as db:
        db.execute("INSERT OR IGNORE INTO members VALUES (?, ?)", (kingdom, player))
    return True


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data, mime="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/gifts/"):
            self.reply(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/gifts/status":
            self.reply(200, json.dumps({"registration": True, "bot": bool(BOT_DB)}).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/api/gifts/register":
            return self.send_error(404)
        if self.headers.get_content_type() != "application/json":
            return self.send_error(415)
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 512:
                return self.send_error(413)
            data = json.loads(self.rfile.read(size))
            player, kingdom = data["player"], data["kingdom"]
            if not re.fullmatch(r"[0-9]{1,20}", player) or not re.fullmatch(r"[1-9][0-9]{0,5}", kingdom):
                raise ValueError()
            if not 0 < int(player) < 2**63:
                raise ValueError()
        except (TypeError, ValueError, KeyError):
            return self.send_error(400)
        try:
            if not register(player, kingdom):
                return self.reply(409, b'{"accepted":false}')
        except (ValueError, sqlite3.Error):
            return self.send_error(503)
        self.reply(200, b'{"accepted":true}')


if __name__ == "__main__":
    if bool(BOT_DB) != bool(GROUP):
        raise SystemExit("Set both NCB_BOT_DB and NCB_GIFT_GROUP")
    if BOT_DB:
        check_group()
    DATABASE.touch(mode=0o600, exist_ok=True)
    with sqlite3.connect(DATABASE) as db:
        db.execute("CREATE TABLE IF NOT EXISTS members (kingdom TEXT, player TEXT, PRIMARY KEY(kingdom, player))")
    ThreadingHTTPServer(("127.0.0.1", 8130), Handler).serve_forever()
