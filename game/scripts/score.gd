extends RefCounted

var points := 0
var combo := 0
var best := 0
var misses := 0
var count := 0
var weight := 0.0
var by_hand := {}
var by_rhythm := {}

static func judge(error: float, windows: Array) -> int:
	for i in range(windows.size()):
		if absf(error) <= windows[i]:
			return 3 - i
	return 0

func record(note: Dictionary, grade: int) -> void:
	note.done = true
	count += 1
	weight += grade / 3.0
	if grade > 0:
		combo += 1
		best = maxi(best, combo)
		points += grade * 100 * multiplier()
	else:
		misses += 1
		combo = 0
	for field in [[by_hand, note.hand], [by_rhythm, note.rhythm]]:
		var totals: Vector2 = field[0].get(field[1], Vector2.ZERO)
		field[0][field[1]] = totals + Vector2(grade / 3.0, 1)

func multiplier() -> int:
	return 1 + mini(3, floori(combo / 8.0))

func accuracy() -> float:
	return weight * 100.0 / maxf(1, count)

func extra_hit() -> void:
	combo = 0
	misses += 1
	count += 1
