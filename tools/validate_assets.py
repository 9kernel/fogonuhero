"""Enforce public content schema and stage a fresh allowlisted Godot project."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from catalog_assets import ROOT

DEMO_AUDIO = ("assets/cortejo.ogg", "assets/cortejo_075.ogg")
PATTERNS = [f"data/rhythms/caixa/cortejo_{section}_{level}.json"
            for section in "ab" for level in ("beginner", "intermediate")]
PUBLIC = (
    "project.godot", "export_presets.cfg", "main.tscn",
    "scripts/main.gd", "scripts/chart.gd", "scripts/score.gd", "scripts/song_clock.gd",
    *DEMO_AUDIO, "data/songs/cortejo.json", *PATTERNS,
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_pattern(data):
    require(data["schema_version"] == 1, "schema_version")
    require(data["validation_status"] in ("approved", "original"), "Mapa pendente")
    require(len(data["time_signature"]) == 2 and all(v > 0 for v in data["time_signature"]), "Compasso")
    require(data["loop_beats"] > 0 and data["notes"], "Loop")
    previous = -1
    for note in data["notes"]:
        require(previous <= note["beat"] < data["loop_beats"] and note["beat"] >= 0, "Posição")
        require(note["hand"] in ("left", "right"), "Mão")
        require(type(note["accent"]) is bool and 0 <= note["velocity"] <= 1, "Acento")
        previous = note["beat"]


def validate(game):
    ids = {}
    for path in PATTERNS:
        data = json.loads((game / path).read_text())
        validate_pattern(data)
        require(data["instrument"] == "caixa", "Instrumento")
        ids[data["rhythm"], data["difficulty"]] = data["id"]
    song = json.loads((game / "data/songs/cortejo.json").read_text())
    require(song["license"] == "CC0-1.0" and song["validation_status"] == "original", "Autorização")
    require(song["audio"] == "res://assets/cortejo.ogg", "Áudio")
    publication = json.loads((ROOT / "docs/publication.json").read_text())
    for filename in DEMO_AUDIO:
        audio = (game / filename).read_bytes()
        approval = publication["files"][filename]
        require(audio.startswith(b"OggS"), "Áudio")
        require(approval["authorized"] is True and approval["license"] == song["license"]
                and hashlib.sha256(audio).hexdigest() == approval["sha256"], "Arquivo de áudio fora da autorização")
    require(song["duration"] > 0, "Duração")
    for events, key in ((song["tempo_map"], "time"), (song["rhythm_sequence"], "start_time")):
        previous = -1
        require(events and events[0][key] == 0, "Origem")
        for event in events:
            require(previous < event[key] < song["duration"], "Ordem dos eventos")
            previous = event[key]
            if key == "time":
                require(event["bpm"] > 0, "BPM")
            else:
                require(all((event["rhythm"], level) in ids for level in song["difficulties"]), "Biblioteca")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path)
    args = parser.parse_args()
    game = ROOT / "game"
    validate(game)
    if args.stage:
        args.stage.mkdir(parents=True, exist_ok=False)
        for name in PUBLIC:
            source = game / name
            require(source.resolve().is_relative_to(game.resolve()), "Caminho externo")
            target = args.stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
