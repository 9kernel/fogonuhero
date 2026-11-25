"""Rank review points by acoustic changes around detected pulses."""
import argparse
from statistics import median

from catalog_assets import LOCAL, ORDERS, save
from index_local_repertoire import read

VERSION = 1


def rank_changes(beats, features, window=4, minimum_space=6.0, maximum=24):
    import numpy as np

    if len(features) < window * 2 + 1:
        return []
    percussive = features[:, :-4]
    spectral = features[:, -4:]
    groups = (percussive, spectral)
    scale = [np.maximum(np.percentile(values, 90, axis=0) - np.percentile(values, 10, axis=0), .05)
             for values in groups]
    changes = np.asarray([
        [np.mean(np.abs(np.median(values[i - window:i], axis=0) -
                        np.median(values[i:i + window], axis=0)) / denominator)
         for values, denominator in zip(groups, scale)]
        for i in range(window, len(features) - window + 1)
    ])
    scores = .75 * changes[:, 0] + .25 * changes[:, 1]
    floor = median(scores) + max(.02, .5 * median(abs(scores - median(scores))))
    peaks = [i for i in range(1, len(scores) - 1)
             if scores[i] >= floor and scores[i - 1] < scores[i] >= scores[i + 1]]
    selected = []
    for peak in sorted(peaks, key=lambda i: scores[i], reverse=True):
        time = float(beats[peak + window])
        if any(abs(time - item["time"]) < minimum_space for item in selected):
            continue
        selected.append({"time": round(time, 3), "contrast": round(float(scores[peak]), 3),
                         "dominant_change": "attacks" if changes[peak, 0] >= changes[peak, 1] else "spectrum"})
        if len(selected) == maximum:
            break
    return sorted(selected, key=lambda item: item["time"])


def suggest(directory):
    import librosa
    import numpy as np
    import soundfile as sf

    analysis = read(directory / "analysis.json")
    output = directory / "transition-suggestions.json"
    if output.is_file():
        cached = read(output)
        if cached.get("method_version") == VERSION and cached.get("source_sha256") == analysis["sha256"]:
            return cached
    y, rate = sf.read(directory / "reference.wav", dtype="float32")
    hop = 256
    mel = librosa.feature.melspectrogram(y=y, sr=rate, hop_length=hop, n_mels=64)
    bands = np.stack([band.sum(axis=0) for band in np.array_split(mel, 4)])
    flux = np.maximum(0, np.diff(np.log1p(bands), axis=1, prepend=np.log1p(bands[:, :1])))
    flux /= np.maximum(.001, np.percentile(flux, 95, axis=1, keepdims=True))
    ratio = bands / np.maximum(1e-8, bands.sum(axis=0, keepdims=True))
    beats = np.asarray(analysis["beats"])
    features = []
    for start, end in zip(beats, beats[1:]):
        first, last = np.round(np.linspace(start, end, 5)[[0, -1]] * rate / hop).astype(int)
        subdivisions = np.array_split(flux[:, first:last], 4, axis=1)
        attacks = [part.mean(axis=1) if part.shape[1] else np.zeros(4) for part in subdivisions]
        spectrum = ratio[:, first:last].mean(axis=1) if last > first and first < ratio.shape[1] else np.zeros(4)
        features.append(np.concatenate([*attacks, spectrum]))
    points = rank_changes(beats, np.asarray(features)) if features else []
    result = {"method_version": VERSION, "source_sha256": analysis["sha256"],
              "status": "draft", "points": points}
    save(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("songs", nargs="+", choices=ORDERS)
    args = parser.parse_args()
    for ident in args.songs:
        song = read(LOCAL / "songs" / f"{ident}.json")
        if not song.get("analysis"):
            parser.error(f"Análise ausente para {ident}")
        directory = (LOCAL / song["analysis"]["report"]).parent
        print(ident, len(suggest(directory)["points"]), "pontos de escuta")
