"""Local onset, beat and pitch-class analysis; all estimates require review."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from catalog_assets import LOCAL, ROOT, save


def analyze(source, rhythm=None, difficulty="unspecified", instrument="caixa"):
    import librosa
    import numpy as np
    import soundfile as sf

    digest = hashlib.file_digest if hasattr(hashlib, "file_digest") else None
    with source.open("rb") as stream:
        if digest:
            fingerprint = digest(stream, "sha256").hexdigest()
        else:
            checksum = hashlib.sha256()
            for block in iter(lambda: stream.read(1048576), b""):
                checksum.update(block)
            fingerprint = checksum.hexdigest()
    directory = LOCAL / "analysis" / (fingerprint + "-v2")
    directory.mkdir(parents=True, exist_ok=True)
    audio = directory / "reference.wav"
    if not audio.exists():
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            extracted = Path(temporary) / "reference.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(source), "-vn",
                            "-ac", "1", "-ar", "22050", str(extracted)], check=True)
            extracted.replace(audio)
    result = directory / "analysis.json"
    if not result.exists():
        y, sr = sf.read(audio, dtype="float32")
        envelope = librosa.onset.onset_strength(y=y, sr=sr)
        tempo, beats = librosa.beat.beat_track(onset_envelope=envelope, sr=sr)
        frames = librosa.onset.onset_detect(onset_envelope=envelope, sr=sr)
        times = librosa.frames_to_time(frames, sr=sr)
        strengths = envelope[frames] / max(1e-6, float(envelope.max()))
        chroma = librosa.feature.chroma_stft(y=y, sr=sr).mean(axis=1)
        profiles = ([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
                    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        ranking = sorted(((float(np.corrcoef(chroma, np.roll(profile, i))[0, 1]), i, m)
                          for m, profile in enumerate(profiles) for i in range(12) if chroma.std() > 0), reverse=True)
        keys = "C C# D Eb E F F# G Ab A Bb B".split()
        relative = source.resolve().relative_to(ROOT) if source.resolve().is_relative_to(ROOT) else source.name
        centered = envelope - envelope.mean()
        correlation = librosa.autocorrelate(centered, max_size=min(len(centered), 350))
        lags = [index for index in range(8, len(correlation) - 1)
                if correlation[index] > 0 and correlation[index - 1] < correlation[index] >= correlation[index + 1]]
        repetition = [dict(seconds=float(librosa.frames_to_time(i, sr=sr)),
                           correlation=float(correlation[i] / correlation[0]))
                      for i in sorted(lags, key=lambda i: correlation[i], reverse=True)[:5]]
        save(result, dict(source=str(relative), sha256=fingerprint, status="draft",
                          bpm=float(np.asarray(tempo).ravel()[0]),
                          beats=librosa.frames_to_time(beats, sr=sr).tolist(),
                          duration=len(y) / sr, channels=1, sample_rate=sr,
                          key_estimate=keys[ranking[0][1]] + ("m" if ranking[0][2] else "") if ranking else None,
                          key_margin=ranking[0][0] - ranking[1][0] if ranking else None,
                          attacks=[dict(time=float(t), strength=float(s), hand="unknown",
                                        technique="unknown", accent=None) for t, s in zip(times, strengths)],
                          attack_intervals=np.diff(times).tolist(), repetition_candidates=repetition,
                          dense_attack_times=[float(times[i]) for i in range(2, len(times))
                                              if times[i] - times[i - 2] < .19],
                          waveform=[float(np.max(np.abs(block))) if block.size else 0
                                    for block in np.array_split(y, 1800)]))
    if rhythm:
        data = json.loads(result.read_text())
        bpm = data["bpm"]
        beats = data["beats"]
        loop = 4
        candidates = []
        # Compare adjacent windows in a provisional sixteenth-note grid.
        if bpm and beats:
            period = 60 / bpm
            attacks = data["attacks"]
            for origin in beats:
                if origin + 2 * loop * period > data["duration"]:
                    break
                groups = [[a for a in attacks if origin + i * loop * period <= a["time"]
                           < origin + (i + 1) * loop * period] for i in range(2)]
                grids = [{round((a["time"] - origin) / period * 4) % (loop * 4)
                          for a in group} for group in groups]
                if grids[0] and grids[1]:
                    overlap = len(grids[0] & grids[1]) / len(grids[0] | grids[1])
                    candidates.append((overlap, origin, groups[0]))
        confidence, origin, group = max(candidates, key=lambda candidate: candidate[0], default=(0, 0, []))
        path = directory / f"{instrument}_{rhythm}_{difficulty}.candidate.json"
        if not path.exists():
            save(path, dict(schema_version=1, id=f"{instrument}_{rhythm}_{difficulty}",
                 instrument=instrument, rhythm=rhythm, difficulty=difficulty, time_signature=None,
                 loop_beats=loop if group else None, validation_status="draft",
                 reference_start_time=origin, reference_bpm=bpm or None, grid_similarity=confidence,
                 source_analysis=result.name, notes=[
                     dict(beat=(a["time"] - origin) * bpm / 60, velocity=a["strength"],
                          hand="unknown", accent=None, technique="unknown") for a in group]))
    return directory


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--rhythm")
    parser.add_argument("--difficulty", default="unspecified")
    parser.add_argument("--instrument", default="caixa")
    args = parser.parse_args()
    print(analyze(args.source, args.rhythm, args.difficulty, args.instrument))
