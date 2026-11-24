import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hold import settle
from letter import read_eml


root = Path(__file__).parent
demo = ["absence.eml", "refund.eml", "injection.eml", "personal.eml"]


def sample_names():
    names = sorted(path.name for path in (root / "samples").glob("*.eml"))
    return [name for name in demo if name in names] + [
        name for name in names if name not in demo
    ]


def load_cards():
    labels = json.loads((root / "labels.json").read_text())
    cards = []

    for name in sample_names():
        facts = read_eml(root / "samples" / name)
        fixture = root / "fixtures" / f"{Path(name).stem}.json"
        try:
            result = json.loads(fixture.read_text())
        except json.JSONDecodeError:
            result = None

        settled = settle(name, facts, result)
        settled["label"] = labels.get(name, {}).get("label", name)
        settled["facts"] = facts
        cards.append(settled)

    return cards


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/cards.json":
            body = json.dumps(load_cards()).encode()
            kind = "application/json"
        elif path in ("/", "/show.html"):
            body = (root / "show.html").read_bytes()
            kind = "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("http://127.0.0.1:8765")
    webbrowser.open("http://127.0.0.1:8765")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
