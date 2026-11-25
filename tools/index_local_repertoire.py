"""Index the block's private recordings, derived arrangements and caixa candidates."""
import argparse
import json
from pathlib import Path

from catalog_assets import LOCAL, ORDERS, ROOT, save
from prepare_playtest import apply_review, prepare
from validate_assets import validate_pattern


def read(path):
    return json.loads(path.read_text())


INSTRUMENTS = ("caixa", "repique", "surdo_primeira", "surdo_segunda", "surdo_terceira", "surdo_marcacao")


def approved_pattern(pattern, candidates):
    if pattern.get("validation_status") != "approved":
        raise ValueError("Aprove o mapa antes de importar")
    validate_pattern(pattern)
    if any(note.get("technique") not in ("stroke", "roll", "fill", "call", "muted", "open") for note in pattern["notes"]):
        raise ValueError("Identifique a técnica de cada nota antes de aprovar")
    fields = ("id", "instrument", "rhythm", "difficulty")
    identity = tuple(pattern.get(key) for key in fields)
    if pattern.get("instrument") not in INSTRUMENTS or not any(
        identity == tuple(candidate.get(key) for key in fields)
        and pattern.get("reference_sha256") == checksum
        for candidate, checksum in candidates
    ):
        raise ValueError("O mapa precisa corresponder ao vídeo e ao candidato catalogados")
    return pattern


def candidate_references():
    for index_name in ("all", "ensemble"):
        path = LOCAL / f"analysis-index-{index_name}.json"
        if not path.is_file():
            continue
        for folder in read(path).values():
            source = LOCAL / folder
            for file in sorted(source.glob("*.candidate.json")):
                analysis = read(source / "analysis.json")
                if (ROOT / analysis["source"]).is_file():
                    review_path = source / "stroke-observations.json"
                    if review_path.is_file():
                        review = read(review_path)
                        if review.get("source_sha256") == analysis["sha256"]:
                            analysis["stroke_observations"] = review["observations"]
                    yield read(file), analysis


def catalog_candidates():
    for candidate, analysis in candidate_references():
        yield candidate, analysis["sha256"]


def main(review_file=None, *, reviewed=None, pattern_file=None, reviewed_pattern=None):
    if review_file:
        reviewed = read(review_file)
    if reviewed is not None:
        if not isinstance(reviewed, dict):
            raise ValueError("Envie um manifesto em formato JSON")
        ident = reviewed.get("id")
        if ident not in ORDERS:
            raise ValueError("Música fora do repertório catalogado")
        apply_review(read(LOCAL / "songs" / f"{ident}.json"), reviewed)

    candidates = list(catalog_candidates())
    patterns = {}
    for pattern, _ in candidates:
        rhythm = pattern["rhythm"]
        if (pattern["instrument"] == "caixa" and pattern["notes"]
                and (rhythm not in patterns or pattern["difficulty"] == "beginner")):
            patterns[rhythm] = pattern
    pattern_dir = LOCAL / "reviewed-patterns"
    if pattern_file:
        reviewed_pattern = read(pattern_file)
    if reviewed_pattern is not None:
        if not isinstance(reviewed_pattern, dict):
            raise ValueError("Envie um mapa em formato JSON")
        incoming_pattern = approved_pattern(reviewed_pattern, candidates)
        key = incoming_pattern["id"] + "-" + incoming_pattern["reference_sha256"]
        save(pattern_dir / (key + ".json"), incoming_pattern)
    instruments = {}
    for file in sorted(pattern_dir.glob("*.json")):
        pattern = approved_pattern(read(file), candidates)
        rhythms = instruments.setdefault(pattern["instrument"], {})
        rhythms.setdefault(pattern["rhythm"], {})[pattern["difficulty"]] = pattern
    for rhythm, levels in instruments.get("caixa", {}).items():
        patterns[rhythm] = levels.get("beginner") or next(iter(levels.values()))
    arrangements = {}
    for file in sorted((LOCAL / "arrangements").glob("*/report.json"), key=lambda path: path.stat().st_mtime):
        report = read(file)
        audio = file.with_name("accompaniment.ogg")
        if audio.is_file():
            arrangements[report["source_sha256"]] = (audio, report)
    songs = []
    for ident in ORDERS:
        song = read(LOCAL / "songs" / f"{ident}.json")
        audio, report = arrangements.get(song.get("analysis", {}).get("sha256"), (None, None))
        preview = audio or (ROOT / song["source"] if song.get("source") else None)
        song["preview"] = preview.relative_to(ROOT).as_posix() if preview and preview.is_file() else None
        song["preview_arranged"] = audio is not None
        review_path = LOCAL / "reviews" / f"{ident}.json"
        incoming = reviewed if reviewed and reviewed["id"] == ident else None
        review = incoming or (read(review_path) if review_path.is_file() else None)
        if review:
            song = apply_review(song, review)
        required = {entry["rhythm"] for entry in song["rhythm_sequence"]}
        if audio and required <= patterns.keys() and (len(song["rhythm_sequence"]) == 1 or review):
            target = LOCAL / "playtest" / ident
            if incoming or not (target / "song.json").is_file():
                selected = {rhythm: patterns[rhythm] for rhythm in sorted(required)}
                session = prepare(song, report, selected)
                session["audio"] = audio.relative_to(ROOT).as_posix()
                save(target / "patterns.json", selected)
                save(target / "song.json", session)
        if incoming:
            save(review_path, incoming)
        songs.append(song)
    save(LOCAL / "repertoire.json", {"songs": songs, "patterns": patterns, "approved_instruments": instruments})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, help="Manifesto aprovado exportado pelo editor")
    parser.add_argument("--pattern", type=Path, help="Mapa de instrumento aprovado no editor")
    args = parser.parse_args()
    try:
        main(args.review, pattern_file=args.pattern)
    except ValueError as error:
        parser.error(str(error))
