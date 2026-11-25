"""Serve the public build and the private repertoire on loopback only."""
import argparse
from functools import lru_cache, partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import re
import subprocess
from threading import Lock
from urllib.parse import parse_qs, urlsplit

from catalog_assets import LOCAL, ORDERS, ROOT, save
from index_local_repertoire import candidate_references, main as refresh, read
from prepare_playtest import reviewed_sequence, validate_times
from verify_web import verify

REVIEW_LOCK = Lock()


def index(reviewed=None, *, reviewed_pattern=None):
    refresh(reviewed=reviewed, reviewed_pattern=reviewed_pattern)
    routes = {}
    repertoire = read(LOCAL / "repertoire.json")
    entries = {}
    for song in repertoire["songs"]:
        ident = song["id"]
        if song["preview"]:
            audio = ROOT / song["preview"]
            suffix = audio.suffix.lower()
            routes[f"/__bloco/{ident}{suffix}"] = audio
            song["preview"] = f"__bloco/{ident}{suffix}"
        base = LOCAL / "playtest" / ident
        if (base / "song.json").is_file():
            manifest = read(base / "song.json")
            audio = base / "accompaniment.ogg" if manifest["audio"] == "accompaniment.ogg" else ROOT / manifest["audio"]
            if audio.is_file():
                url = f"/__bloco/{ident}-game.ogg"
                routes[url] = audio
                alternate = base / "accompaniment_075.ogg"
                slow = ""
                if alternate.is_file():
                    slow = f"__bloco/{ident}-075.ogg"
                    routes["/" + slow] = alternate
                entries[ident] = {"song": manifest, "patterns": read(base / "patterns.json"),
                                  "audio": url.lstrip("/"), "slow": slow}
    repertoire["entries"] = entries
    return json.dumps(repertoire, ensure_ascii=False).encode(), routes


def draft_path(ident):
    return LOCAL / "review-drafts" / f"{ident}.json"


def save_draft(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("Envie um manifesto em formato JSON")
    if "notes" in manifest:
        save_lesson_draft(manifest)
        return
    ident = manifest.get("id")
    if not isinstance(ident, str) or ident not in ORDERS:
        raise ValueError("Música fora do repertório catalogado")
    song = read(LOCAL / "songs" / f"{ident}.json")
    sequence = reviewed_sequence(song, manifest)
    validate_times(sequence, song["duration"], allow_missing=True)
    save(draft_path(ident), {"id": ident, "analysis": {"sha256": song["analysis"]["sha256"]},
                            "validation_status": "draft", "rhythm_sequence": sequence})


def review_bundle(ident):
    if ident not in ORDERS:
        return None
    catalog = read(LOCAL / "repertoire.json")
    song = next((item for item in catalog["songs"] if item["id"] == ident), None)
    if not song or not song.get("source") or not song.get("analysis"):
        return None
    report = LOCAL / song["analysis"]["report"]
    audio = ROOT / song["source"]
    if not report.is_file() or not audio.is_file():
        return None
    song = {key: value for key, value in song.items() if key not in ("source", "preview")}
    if song.get("rhythm_timing_status") == "approved":
        song["validation_status"] = "approved"
    draft = draft_path(ident)
    if draft.is_file():
        saved = read(draft)
        if saved.get("analysis", {}).get("sha256") == song["analysis"]["sha256"]:
            song["rhythm_sequence"] = reviewed_sequence(song, saved)
            song["validation_status"] = "draft"
            song["draft_loaded"] = True
    analysis = read(report)
    suggestion_path = report.with_name("transition-suggestions.json")
    if suggestion_path.is_file():
        hypotheses = read(suggestion_path)
        if hypotheses.get("source_sha256") == analysis["sha256"]:
            analysis["transition_suggestions"] = hypotheses["points"]
    return song, analysis, audio


def lesson_draft_path(key):
    return LOCAL / "lesson-drafts" / (key + ".json")


def save_lesson_draft(manifest):
    fields = ("id", "instrument", "rhythm", "difficulty")
    identity = tuple(manifest.get(field) for field in fields)
    for candidate, analysis in candidate_references():
        if identity == tuple(candidate.get(field) for field in fields) and manifest.get("reference_sha256") == analysis["sha256"]:
            key = candidate["id"] + "-" + analysis["sha256"]
            selected = {field: manifest[field] for field in (*fields, "schema_version", "notes",
                        "time_signature", "loop_beats", "reference_start_time", "reference_bpm", "reference_sha256")}
            selected["validation_status"] = "draft"
            if not isinstance(selected["notes"], list) or any(not isinstance(note, dict) for note in selected["notes"]):
                raise ValueError("Formato de notas inválido")
            save(lesson_draft_path(key), selected)
            return
    raise ValueError("O mapa precisa corresponder ao vídeo catalogado")


def lesson_bundles():
    bundles = {}
    for candidate, analysis in candidate_references():
        checksum = analysis["sha256"]
        key = candidate["id"] + "-" + checksum
        path = LOCAL / "reviewed-patterns" / (key + ".json")
        pattern = read(path) if path.is_file() else dict(candidate, reference_sha256=checksum)
        draft = lesson_draft_path(key)
        if draft.is_file():
            pattern = dict(read(draft), draft_loaded=True)
        bundles[key] = {"title": (ROOT / analysis["source"]).stem,
                        "pattern": pattern, "analysis": analysis,
                        "source": ROOT / analysis["source"]}
    return bundles


@lru_cache(maxsize=96)
def reference_frame(path, _modified, milliseconds):
    frame = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-ss", str(milliseconds / 1000),
         "-i", str(path), "-map", "0:v:0", "-frames:v", "1", "-an",
         "-filter_threads", "1", "-vf", "scale=480:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
        capture_output=True, check=True, timeout=8)
    if not frame.stdout:
        raise ValueError("O vídeo não contém quadro no instante solicitado")
    return frame.stdout


class Handler(SimpleHTTPRequestHandler):
    def valid_host(self):
        port = self.server.server_port
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def respond(self, status, data, mime):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def respond_json(self, status, value):
        self.respond(status, json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def serve_media(self, path):
        size = path.stat().st_size
        start, end = 0, size - 1
        range_header = self.headers.get("Range")
        if range_header:
            match = re.fullmatch(r"bytes=(\d+)-(\d*)", range_header)
            if not match:
                self.send_error(416)
                return
            start = int(match[1])
            end = min(end, int(match[2])) if match[2] else end
            if start > end:
                self.send_error(416)
                return
        self.send_response(206 if range_header else 200)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Type", self.guess_type(path.name))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(end - start + 1))
        if range_header:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as stream:
            stream.seek(start)
            remaining = end - start + 1
            while remaining:
                chunk = stream.read(min(remaining, 65536))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self):
        if not self.valid_host():
            self.send_error(403)
            return
        request = urlsplit(self.path)
        route = request.path
        catalog, routes = self.server.catalogue
        if route == "/__bloco/catalogo.json":
            self.respond(200, catalog, "application/json; charset=utf-8")
        elif route == "/__bloco/editor":
            self.respond(200, (ROOT / "tools/editor.html").read_bytes(), "text/html; charset=utf-8")
        elif route == "/__bloco/levadas.json":
            self.respond_json(200, [
                {"id": ident, "title": bundle["title"],
                 "instrument": bundle["pattern"]["instrument"],
                 "rhythm": bundle["pattern"]["rhythm"],
                 "status": bundle["pattern"]["validation_status"]}
                for ident, bundle in lesson_bundles().items()
            ])
        elif route.startswith("/__bloco/levadas/"):
            ident, _, asset = route.removeprefix("/__bloco/levadas/").partition("/")
            bundle = lesson_bundles().get(ident)
            if not bundle or asset not in ("", "video", "quadro"):
                self.send_error(404)
            elif asset == "video":
                self.serve_media(bundle["source"])
            elif asset == "quadro":
                try:
                    time = float(parse_qs(request.query).get("tempo", [""])[0])
                    if not math.isfinite(time) or not 0 <= time < bundle["analysis"]["duration"]:
                        raise ValueError("Instante fora do vídeo")
                    source = bundle["source"]
                    self.respond(200, reference_frame(source, source.stat().st_mtime_ns, round(time * 1000)), "image/jpeg")
                except ValueError as error:
                    self.respond_json(400, {"error": str(error)})
                except (OSError, subprocess.SubprocessError):
                    self.respond_json(503, {"error": "Não foi possível extrair o quadro com FFmpeg"})
            else:
                self.respond_json(200, {"manifest": bundle["pattern"], "analysis": bundle["analysis"],
                                        "audio": route + "/video"})
        elif route.startswith("/__bloco/revisao/"):
            ident, _, asset = route.removeprefix("/__bloco/revisao/").partition("/")
            bundle = review_bundle(ident)
            if not bundle or asset not in ("", "audio"):
                self.send_error(404)
            elif asset == "audio":
                self.serve_media(bundle[2])
            else:
                self.respond_json(200, {"manifest": bundle[0], "analysis": bundle[1], "audio": route + "/audio"})
        elif route in routes:
            self.serve_media(routes[route])
        else:
            super().do_GET()

    def do_POST(self):
        if (not self.valid_host() or self.headers.get("Origin") != "http://" + str(self.headers.get("Host"))
                or self.headers.get_content_type() != "application/json"):
            self.send_error(403)
            return
        route = urlsplit(self.path).path
        if route not in ("/__bloco/revisao", "/__bloco/levadas", "/__bloco/rascunho"):
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 65536:
                raise ValueError("Manifesto vazio ou acima do limite")
            manifest = json.loads(self.rfile.read(size))
            with REVIEW_LOCK:
                if route == "/__bloco/rascunho":
                    save_draft(manifest)
                elif route == "/__bloco/levadas":
                    self.server.catalogue = index(reviewed_pattern=manifest)
                    lesson_draft_path(manifest["id"] + "-" + manifest["reference_sha256"]).unlink(missing_ok=True)
                else:
                    self.server.catalogue = index(manifest)
                    draft_path(manifest["id"]).unlink(missing_ok=True)
        except (ValueError, KeyError, TypeError) as error:
            self.respond_json(400, {"error": str(error)})
        else:
            self.respond_json(200, {"saved": True})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    verify(ROOT / "build")
    catalogue = index()
    handler = partial(Handler, directory=str(ROOT / "build"))
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        server.catalogue = catalogue
        print(f"http://127.0.0.1:{args.port}/?bloco=1", flush=True)
        server.serve_forever()
