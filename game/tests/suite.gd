extends SceneTree

const Chart = preload("res://scripts/chart.gd")
const Score = preload("res://scripts/score.gd")
var failures := 0

class SilentGame extends "res://scripts/main.gd":
	var played_voices: Array[int] = []
	func play_hit(voice: int, _sound: AudioStreamWAV, _volume: float) -> void:
		played_voices.append(voice)

func check(value: bool, description: String) -> void:
	if not value:
		failures += 1
		push_error(description)

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var song := Chart.read("res://data/songs/cortejo.json")
	var a := Chart.read("res://data/rhythms/caixa/cortejo_a_beginner.json")
	var b := Chart.read("res://data/rhythms/caixa/cortejo_b_beginner.json")
	check(song.id == "cortejo" and a.notes.size() == 4, "Leitura")
	check(Chart.read("res://missing.json").is_empty(), "Ausência")
	var notes := Chart.generate(song, {"cortejo_a": a, "cortejo_b": b})
	check(notes.size() == 32, "Geração")
	check(notes[16].rhythm == "cortejo_b" and is_equal_approx(notes[16].time, song.rhythm_sequence[1].start_time), "Transição")
	var incomplete := song.duplicate(true)
	incomplete.rhythm_sequence[1].start_time = null
	check(Chart.generate(incomplete, {"cortejo_a": a, "cortejo_b": b}).is_empty(), "Transição ausente")
	a.validation_status = "draft"
	check(Chart.generate(song, {"cortejo_a": a, "cortejo_b": b}).is_empty(), "Rascunho")
	check(is_equal_approx(Chart.clock_time([{"time": 0., "bpm": 60.}, {"time": 2., "bpm": 120.}], 1., 3.), 3.), "Andamento")
	check(Score.judge(.045, [.045, .09, .15]) == 3 and Score.judge(.15, [.045, .09, .15]) == 1
		and Score.judge(-.151, [.045, .09, .15]) == 0, "Janelas")
	var points = Score.new()
	points.record(notes[0], 3)
	points.record(notes[1], 2)
	points.record(notes[2], 0)
	check(points.points == 500 and points.combo == 0 and points.best == 2 and points.misses == 1, "Pontuação")
	var game := SilentGame.new()
	game.size = Vector2(540, 860)
	root.add_child(game)
	game.begin()
	game.pause()
	check(game.state == "paused", "Pausa")
	game.menu.get_child(1).pressed.emit()
	check(game.state == "play" and not game.music.stream_paused, "Retomada")
	game.time = 0.0
	game.offset = .2
	game.clock.last = .2
	game.strike(0)
	game.strike(0)
	check(game.score.points == 300 and game.score.combo == 0 and game.score.misses == 1, "Offset e acerto único")
	game.offset = 0
	game.score = Score.new()
	game.clock.last = 1.0
	game.chart = [{"time": 1.0, "hand": "left", "accent": false, "rhythm": "cortejo_a", "done": false},
		{"time": 1.0, "hand": "right", "accent": false, "rhythm": "cortejo_a", "done": false}]
	for i in range(2):
		var event := InputEventScreenTouch.new()
		event.index = i
		event.position = Vector2(game.size.x * (.25 + i * .5), game.size.y * .85)
		event.pressed = true
		game._input(event)
		game._input(event)
	check(game.score.points == 600 and game.score.combo == 2, "Multitoque simultâneo")
	game.mode = "Aprender"
	game.bpm = 96
	game.begin()
	check(game.chart.size() == 16 and is_equal_approx(game.chart[1].time, .625), "Aprender em BPM ajustável")
	game.mode = "Ensaio"
	game.section_choice = 2
	game.speed = .75
	game.begin()
	check(game.rhythm_name == "Cortejo B" and game.chart.size() == 16, "Ensaio por trecho")
	check(is_equal_approx(game.chart[0].time, song.rhythm_sequence[1].start_time / .75)
		and is_equal_approx(game.music.get_stream().get_length(), song.duration / .75), "Áudio e grade a 75%")
	game.mode = "Transições"
	game.begin()
	check(game.rhythm_name == "Cortejo A", "Nome antes da transição")
	game.time = game.active_song.rhythm_sequence[1].start_time
	game.update_rhythm()
	check(game.rhythm_name == "Cortejo B", "Nome atualizado na transição")
	game.local_repertoire["approved_instruments"] = {"repique": {"ijexa": {"beginner": {
		"id": "repique_ijexa_fixture", "instrument": "repique", "difficulty": "beginner",
		"validation_status": "approved", "loop_beats": 2, "reference_bpm": 100,
		"notes": [{"beat": 0.0, "hand": "left", "accent": true}, {"beat": 1.0, "hand": "right", "accent": false}]
	}}}}
	game.select_mode("Aprender")
	var repique_button: Button
	for node in game.menu.get_children():
		if node is Button and node.text == "Repique":
			repique_button = node
	check(repique_button != null, "Instrumento aprovado no seletor")
	if repique_button:
		repique_button.pressed.emit()
		game.menu.get_child(1).pressed.emit()
		game.menu.get_child(1).pressed.emit()
		game.begin()
		check(game.rhythm_name == "Ijexá" and game.chart.size() == 16 and game.bpm == 100, "Mapa aprovado de repique")
		check(game.practice_sound() == game.repique and game.practice_sound() != game.snare, "Timbre do instrumento escolhido")
	var caixa_pattern := a.duplicate(true)
	caixa_pattern.validation_status = "approved"
	var repique_pattern: Dictionary = game.local_repertoire.approved_instruments.repique.ijexa.beginner
	var surdo_pattern := repique_pattern.duplicate(true)
	surdo_pattern.instrument = "surdo_primeira"
	game.local_repertoire.approved_instruments = {
		"caixa": {"cortejo_a": {"beginner": caixa_pattern}},
		"repique": {"cortejo_a": {"beginner": repique_pattern}, "cortejo_b": {"beginner": repique_pattern}},
		"surdo_primeira": {"cortejo_a": {"beginner": surdo_pattern}}
	}
	game.local_song = song
	game.local_patterns = {"cortejo_a": repique_pattern, "cortejo_b": repique_pattern}
	game.local_audio = load("res://assets/cortejo.ogg")
	game.local_practice = false
	game.experimental = true
	game.practice_instrument = "repique"
	game.section_choice = 0
	game.mode = "Apresentação"
	game.begin()
	check(game.can_play_instrument(song, "repique") and not game.can_play_instrument(song, "surdo_primeira"), "Cobertura de cada instrumento")
	check(game.ensemble_layers.has("caixa") and game.ensemble_layers.has("surdo_primeira")
		and not game.ensemble_layers.has("repique"), "Camadas separadas por instrumento")
	check(game.ensemble_layers.surdo_primeira.events.all(func(note): return note.rhythm == "cortejo_a"),
		"Camada incompleta toca só o segmento aprovado")
	game.played_voices.clear()
	game.play_virtual_battery(0)
	check(game.played_voices.has(game.instrument_voices.caixa) and game.played_voices.has(game.instrument_voices.surdo_primeira)
		and not game.played_voices.has(game.instrument_voices.repique), "Apresentação silencia apenas a parte do jogador")
	game.mode = "Ensaio"
	game.begin()
	game.played_voices.clear()
	game.play_virtual_battery(0)
	check(game.played_voices.has(game.instrument_voices.repique), "Ensaio inclui a parte do jogador")
	var advanced_repique := repique_pattern.duplicate(true)
	advanced_repique.difficulty = "advanced"
	advanced_repique.notes.append({"beat": 1.5, "hand": "right", "accent": true})
	game.local_repertoire.approved_instruments.repique.cortejo_a.advanced = advanced_repique
	var choices := game.available_song_levels({"song": song, "patterns": {}}, "repique")
	check(choices.keys() == ["beginner"], "Nível oferecido só com mapa de cada trecho")
	game.local_repertoire.approved_instruments.repique.cortejo_b.advanced = advanced_repique
	choices = game.available_song_levels({"song": song, "patterns": {}}, "repique")
	check(choices.keys() == ["beginner", "advanced"], "Níveis alternativos quando completos")
	game.local_level_choices = choices
	game.select_song_level("advanced")
	game.begin()
	check(game.chart.size() == 48 and is_equal_approx(game.windows[0], .030), "Avançado seleciona o mapa e a janela corretos")
	game.local_repertoire.approved_instruments.repique.cortejo_b.erase("advanced")
	game.local_repertoire.approved_instruments.repique.cortejo_a.erase("beginner")
	choices = game.available_song_levels({"song": song, "patterns": {}}, "repique")
	check(choices.keys() == ["mixed"], "Mapas de níveis distintos mantêm indicação própria")
	game.mode = "Transições"
	game.options()
	check(game.menu.get_children().any(func(node): return node.text == "Cortejo A → Cortejo B"), "Treino nomeia a mudança")
	game.mode = "Ensaio"
	game.select_song_level("beginner")
	game.begin()
	var long_chart := []
	for i in range(7200):
		long_chart.append({"time": i * .0625, "hand": "left", "accent": false, "rhythm": "ijexa", "done": false})
	check(Chart.first_at_or_after([], 1) == 0 and Chart.first_at_or_after(long_chart, 450) == 7200,
		"Busca no início e fim do mapa")
	check(Chart.first_at_or_after(long_chart, 440) == 7040, "Busca em faixa longa")
	game.chart = long_chart
	game.score = Score.new()
	game.next_miss = 0
	game.time = 440.0
	game.clock.last = 440.0
	game.strike(0)
	check(game.chart[7040].done and game.score.points == 300 and game.score.combo == 1,
		"Acerto preservado perto do fim da faixa")
	check(game.score.misses == 7038 and game.next_miss == 7038, "Cursor conta atrasos uma vez")
	game.expire_notes(440.0)
	check(game.score.misses == 7038, "Expiração idempotente")
	game.audio_settings()
	var volume: HSlider = game.menu.get_child(2)
	volume.value = 50
	var music_bus := AudioServer.get_bus_index("Melodia")
	var feedback_bus := AudioServer.get_bus_index("Feedback")
	check(is_equal_approx(AudioServer.get_bus_volume_db(music_bus), linear_to_db(.5)), "Controle do volume")
	check(is_equal_approx(game.prefs.get_value("audio", "Melodia"), 50), "Volume armazenado nas preferências")
	volume.value = 0
	check(AudioServer.is_bus_mute(music_bus) and not AudioServer.is_bus_mute(feedback_bus), "Silêncio por canal independente")
	volume.value = 100
	check(not AudioServer.is_bus_mute(music_bus), "Volume reativa o canal")
	game.queue_free()
	await process_frame
	print("FogonuHero: %d falhas" % failures)
	quit(1 if failures else 0)
