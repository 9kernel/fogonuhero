extends RefCounted

static func read(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if not file:
		return {}
	var value: Variant = JSON.parse_string(file.get_as_text())
	return value if value is Dictionary else {}

static func clock_time(tempo: Array, origin: float, beats: float) -> float:
	var bpm := 120.0
	for event in tempo:
		var time: float = event.time
		if time <= origin:
			bpm = event.bpm
			continue
		var capacity := (time - origin) * bpm / 60.0
		if beats <= capacity:
			break
		beats -= capacity
		origin = time
		bpm = event.bpm
	return origin + beats * 60.0 / bpm

static func generate(song: Dictionary, patterns: Dictionary, experimental := false, allow_missing := false) -> Array:
	var chart := []
	var sections: Array = song.get("rhythm_sequence", [])
	var previous := -1.0
	for section in sections:
		var start: Variant = section.get("start_time")
		if not (start is float or start is int) or start < 0.0 or start <= previous or start >= song.duration:
			return []
		previous = start
		if not patterns.has(section.rhythm):
			if allow_missing:
				continue
			return []
		var pattern: Dictionary = patterns[section.rhythm]
		if (pattern.validation_status not in ["original", "approved"] and not experimental) or pattern.loop_beats <= 0:
			return []
	for s in range(sections.size()):
		var section: Dictionary = sections[s]
		if not patterns.has(section.rhythm):
			continue
		var pattern: Dictionary = patterns[section.rhythm]
		var hits: Array = pattern.notes.duplicate()
		hits.sort_custom(func(a, b): return a.beat < b.beat)
		var end: float = song.duration if s + 1 == sections.size() else sections[s + 1].start_time
		var loop := 0.0
		while clock_time(song.tempo_map, section.start_time, loop) < end - .000001:
			for hit in hits:
				var time := clock_time(song.tempo_map, section.start_time, loop + hit.beat)
				if time < end - .000001:
					var event: Dictionary = hit.duplicate()
					event.merge({"time": time, "rhythm": section.rhythm, "done": false}, true)
					chart.append(event)
			loop += pattern.loop_beats
	return chart


static func first_at_or_after(notes: Array, time: float) -> int:
	var low := 0
	var high := notes.size()
	while low < high:
		var middle := low + floori((high - low) / 2.0)
		if notes[middle].time < time:
			low = middle + 1
		else:
			high = middle
	return low


static func slow_timeline(song: Dictionary, speed: float) -> void:
	song.duration /= speed
	song.bpm *= speed
	for event in song.tempo_map:
		event.time /= speed
		event.bpm *= speed
	for section in song.rhythm_sequence:
		section.start_time /= speed
