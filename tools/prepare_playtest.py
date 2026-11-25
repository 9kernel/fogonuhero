"""Prepare a private Godot playtest from an arrangement and caixa patterns."""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess

from catalog_assets import LOCAL, ORDERS, save


def apply_review(song, reviewed):
    """Apply only approved timings to the original recording and rhythm order."""
    if reviewed.get("validation_status") != "approved":
        raise ValueError("Aprove os tempos no editor antes de importar")
    sequence = reviewed_sequence(song, reviewed)
    validate_times(sequence, song["duration"])
    return dict(song, rhythm_sequence=sequence, rhythm_timing_status="approved")


def reviewed_sequence(song, reviewed):
    if reviewed.get("id") != song["id"]:
        raise ValueError("A revisão precisa corresponder à música do catálogo")
    catalog_hash = song.get("analysis", {}).get("sha256")
    if not catalog_hash or reviewed.get("analysis", {}).get("sha256") != catalog_hash:
        raise ValueError("A revisão precisa corresponder à gravação catalogada")
    sequence = reviewed.get("rhythm_sequence", [])
    if [entry.get("rhythm") for entry in sequence] != [entry["rhythm"] for entry in song["rhythm_sequence"]]:
        raise ValueError("A revisão precisa preservar a sequência catalogada")
    return [{"rhythm": entry["rhythm"], "start_time": entry.get("start_time")} for entry in sequence]


def validate_times(sections, duration, *, allow_missing=False):
    last = -1.0
    for section in sections:
        start = section.get("start_time")
        if start is None and allow_missing:
            continue
        if (type(start) not in (int, float) or not math.isfinite(start)
                or start < 0 or not last < start < duration):
            raise ValueError("Revise os instantes de todas as transições no editor")
        last = start


def prepare(song, report, patterns):
    expected = song.get("analysis", {}).get("sha256")
    if expected and report.get("source_sha256") != expected:
        raise ValueError("O arranjo precisa corresponder ao áudio catalogado")
    required = {section["rhythm"] for section in song["rhythm_sequence"]}
    if set(patterns) != required or any(p["instrument"] != "caixa" for p in patterns.values()):
        raise ValueError("Forneça um mapa de caixa para cada ritmo do manifesto")
    for pattern in patterns.values():
        loop = pattern.get("loop_beats") or 0
        if loop <= 0 or not pattern.get("notes") or any(
            not 0 <= note["beat"] < loop or note["hand"] not in ("left", "right", "unknown")
            for note in pattern["notes"]
        ):
            raise ValueError("Corrija o loop, as posições e as mãos dos mapas")
    if not report["bpm_estimate"] > 0:
        raise ValueError("O relatório precisa conter uma estimativa de BPM")
    sections = [dict(section) for section in song["rhythm_sequence"]]
    if len(sections) == 1 and sections[0]["start_time"] is None:
        sections[0]["start_time"] = next(iter(report["beat_estimates"]), 0)
    validate_times(sections, report["duration"])
    return dict(song, audio="accompaniment.ogg", bpm=report["bpm_estimate"], duration=report["duration"],
                key_original=report["key_estimate"], instruments=["caixa"],
                difficulties=sorted({p["difficulty"] for p in patterns.values()}),
                tempo_map=report.get("tempo_map") or [dict(time=0, bpm=report["bpm_estimate"])],
                validation_status="draft", rhythm_sequence=sections)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arrangement", type=Path, help="Diretório do relatório e acompanhamento")
    parser.add_argument("pattern", nargs="+", type=Path, help="Mapas revisados ou candidatos")
    parser.add_argument("--song", choices=ORDERS, default="alalao")
    parser.add_argument("--manifest", type=Path, help="Manifesto editado com os instantes das transições")
    args = parser.parse_args()
    report = json.loads((args.arrangement / "report.json").read_text())
    song = json.loads((LOCAL / "songs" / f"{args.song}.json").read_text())
    if args.manifest:
        edited = json.loads(args.manifest.read_text())
        try:
            song = apply_review(song, edited)
        except ValueError as error:
            parser.error(str(error))
    patterns = {}
    for path in args.pattern:
        pattern = json.loads(path.read_text())
        if pattern["rhythm"] in patterns:
            parser.error("Selecione um único mapa por ritmo para este ensaio")
        patterns[pattern["rhythm"]] = pattern
    try:
        session = prepare(song, report, patterns)
    except ValueError as error:
        parser.error(str(error))
    destination = LOCAL / "playtest" / session["id"]
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.arrangement / "accompaniment.ogg", destination / "accompaniment.ogg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(destination / "accompaniment.ogg"),
                    "-af", "atempo=0.75,apad", "-t", str(report["duration"] / .75), "-c:a", "libvorbis",
                    str(destination / "accompaniment_075.ogg")], check=True)
    save(destination / "patterns.json", patterns)
    save(destination / "song.json", session)


if __name__ == "__main__":
    main()
