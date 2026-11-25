"""Build the static block edition from explicitly approved arrangements and maps."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from catalog_assets import LOCAL, ORDERS, ROOT, save
from prepare_playtest import validate_times
from validate_assets import PUBLIC, DEMO_AUDIO, PATTERNS, validate_pattern
from verify_web import WEB_FILES, verify

MANIFEST = ROOT / "docs/publication.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else hashlib.sha256(stream.read()).hexdigest()


def release_plan(approval, repertoire, sessions, directory, expected):
    approved_songs = approval.get("repertoire", {})
    missing = sorted(set(expected) - approved_songs.keys())
    if missing:
        raise ValueError("Autorização ausente para: " + ", ".join(missing))
    manifest = {"songs": [], "entries": {}, "patterns": {}, "approved_instruments": {}}
    assets = {}
    by_id = {song["id"]: song for song in repertoire["songs"]}
    permitted = {}
    for instrument, data in repertoire.get("approved_instruments", {}).items():
        for rhythm, levels in data.items():
            for level, pattern in levels.items():
                rights = approval.get("patterns", {}).get(pattern["id"], {})
                if (rights.get("authorized") is not True or not rights.get("permission_reference")
                        or not rights.get("license") or rights.get("sha256") != pattern_checksum(pattern)
                        or pattern.get("validation_status") != "approved"):
                    continue
                validate_pattern(pattern)
                permitted.setdefault(instrument, {}).setdefault(rhythm, {})[level] = dict(
                    public_pattern(pattern), license=rights["license"])
    caixa = permitted.get("caixa", {})
    for ident, routine in expected.items():
        rights = approved_songs[ident]
        if rights.get("authorized") is not True or not rights.get("license") or not rights.get("permission_reference"):
            raise ValueError(f"Autorização incompleta para {ident}")
        song = by_id[ident]
        sequence = song["rhythm_sequence"]
        if song.get("rhythm_timing_status") != "approved" or [item["rhythm"] for item in sequence] != routine:
            raise ValueError(f"Revise os tempos e a ordem das levadas de {ident}")
        session = read(sessions / ident / "song.json")
        if (session.get("id") != ident or session.get("rhythm_sequence") != sequence
                or session.get("analysis", {}).get("sha256") != song.get("analysis", {}).get("sha256")):
            raise ValueError(f"Atualize a sessão de {ident} com a revisão dos tempos")
        validate_times(sequence, session["duration"])
        selected = {}
        for rhythm in sorted(set(routine)):
            levels = caixa.get(rhythm, {})
            pattern = levels.get("beginner") or next(iter(levels.values()), None)
            if not pattern or pattern.get("validation_status") != "approved":
                raise ValueError(f"Mapa de caixa sem aprovação de publicação: {rhythm}")
            validate_pattern(pattern)
            selected[rhythm] = pattern
        normal = session["audio"]
        audio = sessions / ident / normal if normal == "accompaniment.ogg" else directory / normal
        if (audio.name != "accompaniment.ogg" or
                not (audio.resolve().is_relative_to(sessions.resolve()) or
                     audio.resolve().is_relative_to((directory / ".local/arrangements").resolve()))):
            raise ValueError(f"Origem do arranjo fora dos diretórios de ensaio: {ident}")
        path = f"audio/{ident}.ogg"
        with audio.open("rb") as stream:
            signature = stream.read(4)
        if signature != b"OggS" or checksum(audio) != rights.get("sha256"):
            raise ValueError(f"O áudio de {ident} diverge do arquivo autorizado")
        assets[path] = audio
        slow = ""
        if rights.get("slow_sha256"):
            alternate = sessions / ident / "accompaniment_075.ogg"
            with alternate.open("rb") as stream:
                signature = stream.read(4)
            if signature != b"OggS" or checksum(alternate) != rights["slow_sha256"]:
                raise ValueError(f"O áudio lento de {ident} diverge do arquivo autorizado")
            slow = f"audio/{ident}-075.ogg"
            assets[slow] = alternate
        public = {key: session[key] for key in ("id", "title", "bpm", "duration", "tempo_map", "rhythm_sequence")}
        public["rhythm_sequence"] = [{key: item[key] for key in ("rhythm", "start_time")} for item in sequence]
        public["tempo_map"] = [{key: item[key] for key in ("time", "bpm")} for item in session["tempo_map"]]
        common_levels = set.intersection(*(set(caixa[rhythm]) for rhythm in selected))
        public["difficulties"] = sorted(common_levels) if common_levels else ["mixed"]
        public["license"] = rights["license"]
        manifest["songs"].append(public)
        manifest["entries"][ident] = {"song": public,
            "patterns": selected,
            "audio": path, "audio_sha256": rights["sha256"],
            "slow": slow, "slow_sha256": rights.get("slow_sha256", "")}
    rhythms = {rhythm for routine in expected.values() for rhythm in routine}
    manifest["approved_instruments"] = {
        instrument: {rhythm: levels for rhythm, levels in data.items() if rhythm in rhythms}
        for instrument, data in permitted.items()
    }
    return manifest, assets


def public_pattern(pattern):
    public = {key: pattern[key] for key in ("id", "schema_version", "instrument", "rhythm", "difficulty",
                                           "validation_status", "time_signature", "loop_beats", "reference_bpm")
              if key in pattern}
    public["notes"] = [{key: note[key] for key in ("beat", "hand", "accent", "velocity", "technique")
                        if key in note} for note in pattern["notes"]]
    return public


def pattern_checksum(pattern):
    canonical = json.dumps(public_pattern(pattern), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_bundle(site, manifest):
    """Verify the unpacked site against the authorized plan, independent of staging."""
    verify(site, repertoire=True)
    if read(site / "catalogo.json") != manifest:
        raise ValueError("O catálogo exportado diverge do plano autorizado")
    media = {}
    for entry in manifest["entries"].values():
        media[entry["audio"]] = entry["audio_sha256"]
        if entry["slow"]:
            media[entry["slow"]] = entry["slow_sha256"]
    expected = set(WEB_FILES) | {"catalogo.json", ".nojekyll", *media}
    files = set()
    for path in site.rglob("*"):
        relative = path.relative_to(site).as_posix()
        if path.is_symlink():
            raise ValueError(f"Link simbólico no pacote: {relative}")
        if path.is_file():
            files.add(relative)
        elif relative != "audio":
            raise ValueError(f"Diretório inesperado no pacote: {relative}")
    if files != expected:
        raise ValueError(f"Arquivos do site divergentes: {sorted(files ^ expected)}")
    if (site / ".nojekyll").stat().st_size:
        raise ValueError("Arquivo .nojekyll inesperado")
    for name, sha256 in media.items():
        path = site / name
        with path.open("rb") as stream:
            signature = stream.read(4)
        if signature != b"OggS" or checksum(path) != sha256:
            raise ValueError(f"O áudio empacotado não corresponde à autorização: {name}")
    return len(media)


def build(output, manifest, assets):
    if output.exists():
        raise ValueError("Escolha uma pasta de saída nova")
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary)
        game = stage / "game"
        site = stage / "site"
        site.mkdir()
        ignored = {*DEMO_AUDIO, *PATTERNS, "data/songs/cortejo.json"}
        for name in set(PUBLIC) - ignored:
            target = game / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / "game" / name, target)
        presets = game / "export_presets.cfg"
        contents = presets.read_text(encoding="utf-8")
        for name in DEMO_AUDIO:
            contents = contents.replace(f', "res://{name}"', "")
        presets.write_text(contents, encoding="utf-8")
        subprocess.run(["godot", "--headless", "--path", str(game), "--editor", "--import", "--quit"], check=True)
        subprocess.run(["godot", "--headless", "--path", str(game), "--export-release", "Web", str(site / "index.html")],
                       check=True)
        for name in ("app.js", "styles.css", "GODOT-NOTICES.txt"):
            shutil.copyfile(ROOT / "web" / name, site / name)
        html = (ROOT / "web/index.html").read_text(encoding="utf-8")
        html = html.replace('<html lang="pt-BR">', '<html lang="pt-BR" data-release="repertoire">')
        html = html.replace("Treine sua batida em duas pistas ao som de Cortejo de Neon.", "Toque as levadas do bloco em duas pistas.")
        html = html.replace("Trilha e sons originais do FogonuHero", "FogonuHero · Repertório do bloco")
        (site / "index.png").unlink(missing_ok=True)
        (site / "index.html").write_text(html, encoding="utf-8")
        save(site / "catalogo.json", manifest)
        for name, audio in assets.items():
            target = site / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(audio, target)
        (site / ".nojekyll").touch()
        verify_bundle(site, manifest)
        shutil.move(site, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--verify-only", action="store_true", help="Conferir um pacote já exportado")
    args = parser.parse_args()
    try:
        expected = {ident: data[4].split() for ident, data in ORDERS.items() if data[1]}
        approval = read(MANIFEST)
        if not set(expected) <= approval.get("repertoire", {}).keys():
            raise ValueError("Faltam autorizações dos arranjos do repertório em docs/publication.json")
        manifest, assets = release_plan(approval, read(LOCAL / "repertoire.json"), LOCAL / "playtest", ROOT, expected)
        if args.verify_only:
            print(f"Pacote verificado: {verify_bundle(args.output.resolve(), manifest)} arquivos de áudio autorizados.")
        else:
            build(args.output.resolve(), manifest, assets)
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))
