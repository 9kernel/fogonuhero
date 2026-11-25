"""Separate local stems, transcribe melodic parts, and render with Tunerize."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from analyze import analyze
from catalog_assets import LOCAL, save
from midi_arrangement import limit_voices, tempo_events, write as write_midi

TUNERIZE = "059224e7d4e91c244c2ae99707ea7f5eeaef75f7"


def convert(source, tunerize, transpose):
    import pretty_midi
    from basic_pitch.inference import predict

    revision = subprocess.check_output(["git", "-C", str(tunerize), "rev-parse", "HEAD"], text=True).strip()
    if revision != TUNERIZE:
        raise ValueError(f"Use o commit do Tunerize {TUNERIZE}")
    sys.path.insert(0, str(tunerize.resolve()))
    from app.core.chiptune import render

    analysis = json.loads((analyze(source) / "analysis.json").read_text())
    version = hashlib.sha256(Path(__file__).read_bytes()
                             + Path(__file__).with_name("midi_arrangement.py").read_bytes()).hexdigest()[:12]
    output = LOCAL / "arrangements" / f"{analysis['sha256']}-{version}-{transpose}"
    report = output / "report.json"
    if report.exists() and all((output / f"accompaniment.{ext}").is_file() for ext in ("mid", "wav", "ogg")):
        return output
    output.mkdir(parents=True, exist_ok=True)
    roles = {"vocals": 80, "bass": 38, "other": 81}
    stem_cache = LOCAL / "stem-cache" / f"{analysis['sha256']}-htdemucs-4.0.1"
    stems = stem_cache / "htdemucs" / source.stem
    if not all((stems / f"{role}.wav").is_file() for role in roles):
        # Reuse verified outputs created before stem caching moved out of the arrangement.
        relative_stems = Path("stems") / "htdemucs" / source.stem
        previous = next((path / relative_stems for path in output.parent.glob(analysis["sha256"] + "-*")
                         if (path / "report.json").is_file()), None)
        if previous and all((previous / f"{role}.wav").is_file() for role in roles):
            shutil.copytree(previous, stems, dirs_exist_ok=True)
        else:
            subprocess.run([sys.executable, "-m", "demucs", "-n", "htdemucs", "-o",
                            str(stem_cache), str(source.resolve())], check=True)
    midi = pretty_midi.PrettyMIDI(initial_tempo=analysis["bpm"] or 120)
    counts = {}
    for role, program in roles.items():
        _, transcription, _ = predict(str(stems / f"{role}.wav"), minimum_note_length=80)
        instrument = pretty_midi.Instrument(program, name=role)
        for part in transcription.instruments:
            for note in part.notes:
                pitch = note.pitch + transpose
                if not part.is_drum and 0 <= pitch <= 127:
                    instrument.notes.append(pretty_midi.Note(note.velocity, pitch, note.start, note.end))
        counts[role] = len(instrument.notes)
        if instrument.notes:
            midi.instruments.append(instrument)
    discarded = limit_voices(midi)
    tempos = tempo_events(analysis["beats"], analysis["bpm"] or 120)
    write_midi(midi, output / "accompaniment.mid", tempos)
    raw = output / "render.wav"
    render(midi, raw, engine="snes")
    wav = output / "accompaniment.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", "apad",
                    "-t", str(analysis["duration"]), str(wav)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "libvorbis",
                    str(output / "accompaniment.ogg")], check=True)
    raw.unlink()
    save(report, dict(source_sha256=analysis["sha256"], duration=analysis["duration"], bpm_estimate=analysis["bpm"],
        beat_estimates=analysis["beats"], key_estimate=analysis["key_estimate"], key_margin=analysis["key_margin"],
        transpose=transpose, notes_by_stem=counts, voice_limit=8, notes_dropped_for_polyphony=discarded,
        tempo_map=[dict(time=t, bpm=60000000 / us) for t, us in tempos], tunerize=revision, status="draft",
        distribution=False, discarded_stem="drums", quality="requires listening review"))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--tunerize", type=Path, required=True)
    parser.add_argument("--transpose", type=int, default=0, help="Semitons confirmados pelo revisor")
    args = parser.parse_args()
    print(convert(args.source, args.tunerize, args.transpose))
