"""Generate the original, redistributable FogonuHero demo."""
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile
import wave

GAME = Path(__file__).resolve().parents[1] / "game"


def write(relative, value):
    path = GAME / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    for name, hits in {
        "cortejo_a": [(0, "left"), (1, "right"), (2, "left"), (3.5, "right")],
        "cortejo_b": [(0, "right"), (.5, "left"), (2, "right"), (3, "left")],
    }.items():
        for difficulty in ("beginner", "intermediate"):
            ident = f"{name}_{difficulty}"
            notes = hits if difficulty == "beginner" else sorted(hits + [(1.5, "left"), (2.5, "right")])
            write(f"data/rhythms/caixa/{ident}.json", dict(
                schema_version=1, id=ident, instrument="caixa", rhythm=name,
                difficulty=difficulty, time_signature=[4, 4], loop_beats=4,
                validation_status="original", notes=[
                    dict(beat=beat, hand=hand, accent=i == 0, velocity=1 if i == 0 else .65)
                    for i, (beat, hand) in enumerate(notes)]))
    write("data/songs/cortejo.json", dict(
        id="cortejo", title="Cortejo de Neon", artist="FogonuHero", key_original="Am",
        key_target="Am", bpm=112, duration=32 * 60 / 112,
        tempo_map=[dict(time=0, bpm=112)], audio="res://assets/cortejo.ogg",
        rhythm_sequence=[dict(rhythm="cortejo_a", start_time=0),
                         dict(rhythm="cortejo_b", start_time=16*60/112)],
        instruments=["caixa"], difficulties=["beginner", "intermediate"],
        validation_status="original", license="CC0-1.0"))
    rate = 22050
    chords = [(57, 60, 64), (53, 57, 60), (60, 64, 67), (55, 59, 62)]
    pcm = bytearray()
    for i in range(round(rate * 32 * 60 / 112)):
        t = i / rate
        beat = t * 112 / 60
        chord = chords[int(beat / 4) % len(chords)]
        step = int(beat * 2)
        age = (beat * 2 % 1) * 30 / 112
        def tone(note):
            phase = math.tau * (440 * 2 ** ((note - 69) / 12)) * t
            return math.sin(phase) + .23 * math.sin(2 * phase) + .1 * math.sin(3 * phase)
        melody = tone(chord[(0, 1, 2, 1, 0, 2, 1, 2)[step % 8]] + 12)
        bass = tone(chord[0] - 12)
        sample = .22 * melody * min(1, age * 400) * math.exp(-age * 12)
        sample += .15 * bass * min(1, (beat % 1) * 45) * math.exp(-(beat % 1) * 3)
        pcm.extend(struct.pack("<h", int(sample * 30000)))
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "demo.wav"
        with wave.open(str(source), "wb") as output:
            output.setparams((1, 2, rate, 0, "NONE", ""))
            output.writeframes(pcm)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(source),
                        "-c:a", "libvorbis", str(GAME / "assets/cortejo.ogg")], check=True)

    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(GAME / "assets/cortejo.ogg"),
                    "-af", "atempo=0.75,apad", "-t", str(32 * 60 / (112 * .75)), "-c:a", "libvorbis",
                    str(GAME / "assets/cortejo_075.ogg")], check=True)


if __name__ == "__main__":
    main()
