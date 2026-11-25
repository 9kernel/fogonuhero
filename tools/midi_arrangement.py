"""Prepare a limited-polyphony SMF with the same note times as the source."""
from bisect import bisect_right
from statistics import median


def limit_voices(midi, maximum=8):
    events = sorted((note.start, rank, -note.velocity, i, note)
                    for rank, part in enumerate(midi.instruments) for i, note in enumerate(part.notes))
    active = []
    kept = [[] for _ in midi.instruments]
    discarded = 0
    for start, rank, _, _, note in events:
        active = [end for end in active if end > start]
        if len(active) < maximum:
            active.append(note.end)
            kept[rank].append(note)
        else:
            discarded += 1
    for part, notes in zip(midi.instruments, kept):
        part.notes = notes
    return discarded


def tempo_events(beats, fallback):
    intervals = [end - start for start, end in zip(beats, beats[1:])]
    usable = [delta for delta in intervals if .25 <= delta <= 1.5]
    baseline = median(usable) if usable else 60 / fallback
    tempos = [(0.0, round(baseline * 1e6))]
    for i, delta in enumerate(intervals):
        if not .25 <= delta <= 1.5:
            continue
        neighbors = [d for d in intervals[max(0, i - 2):i + 3] if .25 <= d <= 1.5]
        value = round(median(neighbors) * 1e6)
        if abs(tempos[-1][1] - value) > 1000:
            if beats[i] == 0:
                tempos[-1] = (0.0, value)
            else:
                tempos.append((beats[i], value))
    return tempos


def write(midi, path, tempos):
    import mido

    resolution = 960
    output = mido.MidiFile(ticks_per_beat=resolution)
    tempo_track = mido.MidiTrack()
    output.tracks.append(tempo_track)
    locations = [0]
    starts = [time for time, _ in tempos]
    for (start, tempo), (following, _) in zip(tempos, tempos[1:]):
        locations.append(locations[-1] + mido.second2tick(following - start, resolution, tempo))
    for i, (_, tempo) in enumerate(tempos):
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=tempo,
                           time=locations[i] - locations[i - 1] if i else 0))

    def tick(second):
        i = bisect_right(starts, second) - 1
        return locations[i] + mido.second2tick(second - starts[i], resolution, tempos[i][1])

    for channel, part in enumerate(midi.instruments):
        track = mido.MidiTrack()
        output.tracks.append(track)
        track.append(mido.MetaMessage("track_name", name=part.name))
        track.append(mido.Message("program_change", channel=channel, program=part.program))
        events = []
        for note in part.notes:
            start = tick(note.start)
            events.append((start, True, note.pitch, note.velocity))
            events.append((max(start + 1, tick(note.end)), False, note.pitch, 0))
        previous = 0
        for position, on, pitch, velocity in sorted(events):
            track.append(mido.Message("note_on" if on else "note_off", channel=channel,
                                      note=pitch, velocity=velocity, time=position - previous))
            previous = position
    output.save(str(path))
