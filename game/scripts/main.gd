extends Control

const Chart = preload("res://scripts/chart.gd")
const Score = preload("res://scripts/score.gd")
const SongClock = preload("res://scripts/song_clock.gd")
const DEMO_AUDIO = ["res://assets/cortejo.ogg", "res://assets/cortejo_075.ogg"]
var public_repertoire := false
const COLORS := [Color("#55e7cc"), Color("#fa77b2")]
var song := Chart.read("res://data/songs/cortejo.json")
var chart: Array = []
var next_miss := 0
var local_catalog := {}
var local_repertoire := {}
var workspace := ""
var local_practice := false
var practice_instrument := "caixa"
var practice_pattern := {}
const INSTRUMENT_NAMES := {
	"caixa": "Caixa de guerra", "repique": "Repique",
	"surdo_primeira": "Surdo de primeira", "surdo_segunda": "Surdo de segunda",
	"surdo_terceira": "Surdo de terceira", "surdo_marcacao": "Surdo de marcação"
}
var practice_sounds := {}
var ensemble_layers := {}
var instrument_voices := {}
var local_song := {}
var local_patterns := {}
var local_level_choices := {}
const LEVEL_NAMES := {
	"beginner": "Iniciante", "intermediate": "Intermediário", "advanced": "Avançado",
	"unspecified": "Nível não especificado", "mixed": "Mapas disponíveis"
}
var local_audio: AudioStreamOggVorbis
var local_slow_audio: AudioStreamOggVorbis
var experimental := false
var active_song: Dictionary
var score = Score.new()
var clock = SongClock.new()
var music := AudioStreamPlayer.new()
var hits: Array[AudioStreamPlayer] = []
var click: AudioStreamWAV
var snare: AudioStreamWAV
var surdo: AudioStreamWAV
var repique: AudioStreamWAV
var next_ensemble := 0.0
var menu: VBoxContainer
var state := "menu"
var mode := "Ensaio"
var pattern := "cortejo_a"
var difficulty := "beginner"
var bpm := 112.0
var speed := 1.0
var section_choice := 0
var transition_choice := 1
var offset := 0.0
var bind := [KEY_F, KEY_J]
var rebinding := -1
var windows := [.045, .090, .150]
var window_scale := 1.0
var visibility_callback: JavaScriptObject
var start_at := 0
var paused_at := 0
var last_audio_advance := 0
var time := 0.0
var shift := 0.0
var next_beat := 0.0
var next_kit := 0
var countdown_tick := -4
var calibration: Array[float] = []
var flash := [0, 0]
var pointers := {}
var banner := ""
var rhythm_name := ""
const RHYTHM_NAMES := {
	"cortejo_a": "Cortejo A", "cortejo_b": "Cortejo B", "ijexa": "Ijexá",
	"samba": "Samba", "samba_reggae": "Samba-reggae", "baiao_xote": "Baião/Xote",
	"marchinha": "Marchinha", "maracatu": "Maracatu", "rumba": "Rumba", "maculele": "Maculelê"
}
const MIXER_LABELS := {
	"Melodia": "Acompanhamento", "Caixa": "Caixa virtual", "Repique": "Repique virtual",
	"Surdos": "Surdos virtuais", "Metrônomo": "Metrônomo", "Feedback": "Batidas do jogador"
}
var mixer_levels := {}
var prefs := ConfigFile.new()
var vibration := false
var repeat_practice := false

func _ready() -> void:
	if OS.has_feature("web"):
		public_repertoire = JavaScriptBridge.eval("document.documentElement.dataset.release === 'repertoire'", true)
		var preview: bool = JavaScriptBridge.eval(
			"['127.0.0.1','localhost'].includes(location.hostname) && new URLSearchParams(location.search).get('bloco') === '1'", true)
		if public_repertoire or preview:
			var data := await fetch_private("catalogo.json" if public_repertoire else "__bloco/catalogo.json")
			var parsed: Variant = JSON.parse_string(data.get_string_from_utf8())
			if parsed is Dictionary and parsed.has("entries"):
				local_repertoire = parsed
				local_catalog = parsed.entries
	if not OS.has_feature("web") and not OS.has_feature("template"):
		workspace = ProjectSettings.globalize_path("res://").path_join("../")
		local_repertoire = Chart.read(workspace.path_join(".local/repertoire.json"))
		var base := workspace.path_join(".local/playtest")
		catalog_local(base)
		for directory in DirAccess.get_directories_at(base):
			catalog_local(base.path_join(directory))
	add_child(music)
	music.playback_type = AudioServer.PLAYBACK_TYPE_SAMPLE if OS.has_feature("web") else AudioServer.PLAYBACK_TYPE_STREAM
	for bus in MIXER_LABELS:
		if AudioServer.get_bus_index(bus) < 0:
			AudioServer.add_bus()
			AudioServer.set_bus_name(AudioServer.bus_count - 1, bus)
	music.bus = "Melodia"
	var buses := ["Feedback", "Feedback", "Caixa", "Metrônomo", "Surdos", "Repique"]
	for i in range(buses.size()):
		var voice := AudioStreamPlayer.new()
		voice.max_polyphony = 4
		voice.bus = buses[i]
		add_child(voice)
		hits.append(voice)
	for id in INSTRUMENT_NAMES:
		var voice := AudioStreamPlayer.new()
		voice.max_polyphony = 4
		var bus := "Surdos"
		if id == "caixa":
			bus = "Caixa"
		elif id == "repique":
			bus = "Repique"
		voice.bus = bus
		add_child(voice)
		instrument_voices[id] = hits.size()
		hits.append(voice)
	click = synth(false)
	snare = synth(true)
	surdo = synth(false, 75.0, 27.0)
	repique = synth(false, 360.0, 58.0)
	practice_sounds = {"caixa": snare, "repique": repique, "surdo_primeira": synth(false, 65.0, 25.0),
		"surdo_segunda": synth(false, 87.0, 29.0), "surdo_terceira": synth(false, 111.0, 35.0),
		"surdo_marcacao": surdo}
	prefs.load("user://fogonuhero.cfg")
	for bus in MIXER_LABELS:
		set_mixer_level(bus, float(prefs.get_value("audio", bus, 100)))
	offset = prefs.get_value("controls", "offset", 0.0)
	bind = prefs.get_value("controls", "keys", [KEY_F, KEY_J])
	vibration = prefs.get_value("controls", "vibration", false)
	window_scale = prefs.get_value("controls", "window_scale", 1.0)
	var theme_resource := Theme.new()
	theme_resource.default_font_size = 24
	theme = theme_resource
	var frame := CenterContainer.new()
	frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(frame)
	frame.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	menu = VBoxContainer.new()
	menu.custom_minimum_size.x = 330
	menu.add_theme_constant_override("separation", 10)
	frame.add_child(menu)
	home()
	if OS.has_feature("web"):
		JavaScriptBridge.eval("document.documentElement.dataset.gameReady = 'true'")
		visibility_callback = JavaScriptBridge.create_callback(_visibility_changed)
		JavaScriptBridge.get_interface("document").addEventListener("visibilitychange", visibility_callback)

func fetch_private(url: String) -> PackedByteArray:
	var request := HTTPRequest.new()
	request.timeout = 20.0
	add_child(request)
	var base: String = JavaScriptBridge.eval("new URL('.', location.href).href", true)
	if request.request(base + url) != OK:
		request.queue_free()
		return PackedByteArray()
	var response: Array = await request.request_completed
	request.queue_free()
	return response[3] if response[0] == HTTPRequest.RESULT_SUCCESS and response[1] == 200 else PackedByteArray()

func private_stream(path: String) -> AudioStream:
	if OS.has_feature("web"):
		var bytes := await fetch_private(path)
		if bytes.is_empty():
			return null
		if path.get_extension() == "mp3":
			return AudioStreamMP3.load_from_buffer(bytes)
		return AudioStreamOggVorbis.load_from_buffer(bytes)
	if path.get_extension() == "mp3":
		return AudioStreamMP3.load_from_file(path)
	return AudioStreamOggVorbis.load_from_file(path)

func catalog_local(base: String) -> void:
	var manifest := Chart.read(base.path_join("song.json"))
	var patterns := Chart.read(base.path_join("patterns.json"))
	if not manifest.is_empty() and not patterns.is_empty():
		var audio := base.path_join("accompaniment.ogg")
		if manifest.get("audio", "") != "accompaniment.ogg":
			audio = workspace.path_join(manifest.audio)
		if FileAccess.file_exists(audio):
			local_catalog[manifest.id] = {"song": manifest, "patterns": patterns, "path": base, "audio": audio}

func select_local(id: String) -> bool:
	var entry: Dictionary = local_catalog[id]
	if not can_play_instrument(entry.song, practice_instrument):
		return false
	var slow_path: String = entry.get("slow", "")
	if not OS.has_feature("web"):
		var alternate: String = entry.path.path_join("accompaniment_075.ogg")
		if FileAccess.file_exists(alternate):
			slow_path = alternate
	local_audio = await private_stream(entry.audio) as AudioStreamOggVorbis
	local_slow_audio = null
	if not slow_path.is_empty():
		local_slow_audio = await private_stream(slow_path) as AudioStreamOggVorbis
	if not local_audio:
		return false
	local_song = entry.song
	local_level_choices = available_song_levels(entry, practice_instrument)
	if local_level_choices.is_empty():
		return false
	select_song_level(local_level_choices.keys()[0])
	experimental = true
	return true

func _visibility_changed(_args: Array) -> void:
	if JavaScriptBridge.get_interface("document").hidden:
		pause()

func synth(noise: bool, frequency := 1000.0, decay := 65.0) -> AudioStreamWAV:
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = 22050
	var data := PackedByteArray()
	data.resize(3600)
	var rng := RandomNumberGenerator.new()
	rng.seed = 93
	for i in range(1800):
		var t := i / 22050.0
		var sample := sin(TAU * (170 if noise else frequency) * t)
		if noise:
			sample = sample * .25 + rng.randf_range(-.75, .75)
		data.encode_s16(i * 2, int(sample * exp(-t * decay) * 18000))
	stream.data = data
	return stream

func play_hit(voice: int, sound: AudioStreamWAV, volume: float) -> void:
	if hits[voice].stream != sound:
		hits[voice].stream = sound
	hits[voice].volume_db = volume
	hits[voice].play()

func web_status(title: String) -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("document.documentElement.dataset.gameScreen = " + JSON.stringify(title))
		if title not in ["Partida", "Pausa"]:
			JavaScriptBridge.eval("document.getElementById('rhythm-status')?.replaceChildren()", true)

func screen(title: String) -> void:
	web_status(title)
	for child in menu.get_children():
		menu.remove_child(child)
		child.queue_free()
	menu.show()
	label(title, 35)

func label(value: String, font_size := 21) -> void:
	var node := Label.new()
	node.text = value
	node.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	node.add_theme_font_size_override("font_size", font_size)
	menu.add_child(node)

func button(title: String, action: Callable) -> void:
	var node := Button.new()
	node.text = title
	node.custom_minimum_size.y = 49
	node.focus_mode = Control.FOCUS_NONE
	node.pressed.connect(action)
	var style := StyleBoxFlat.new()
	style.bg_color = Color("#29254b")
	style.border_color = Color("#65568e")
	style.set_border_width_all(2)
	node.add_theme_stylebox_override("normal", style)
	menu.add_child(node)

func home() -> void:
	music.stop()
	state = "menu"
	rebinding = -1
	screen("FOGONUHERO")
	label("BATERIA DE RUA   •   REPERTÓRIO DO BLOCO" if not local_repertoire.is_empty() else "BATERIA DE RUA   •   EDIÇÃO DEMO")
	if public_repertoire and local_repertoire.is_empty():
		label("O repertório está indisponível. Recarregue a página.", 18)
		return
	button("Jogar", func(): select_mode("Ensaio"))
	button("Aprender ritmos", func(): select_mode("Aprender"))
	button("Treinar transições", func(): select_mode("Transições"))
	button("Tutorial", tutorial)
	button("Configurações", settings)
	button("Créditos", credits)

func tutorial() -> void:
	screen("Como tocar")
	label("Acerte a nota quando cruzar a linha.\nO contorno dourado indica acento.\nUse as teclas configuradas ou toque\nnas áreas esquerda e direita.")
	button("Voltar", home)

func credits() -> void:
	screen("Créditos")
	if public_repertoire:
		label("FogonuHero · Repertório do bloco", 20)
		for item in local_repertoire.songs:
			label("%s · %s" % [item.title, item.license], 17)
	elif not local_repertoire.is_empty():
		label("FogonuHero • sons sintetizados\nLeituras locais dos materiais do bloco.")
	else:
		label("Cortejo de Neon • trilha e padrões originais\nSons sintetizados pelo FogonuHero.")
	button("Voltar", home)

func instrument_patterns(manifest: Dictionary, instrument: String, level: String) -> Dictionary:
	var instruments: Dictionary = local_repertoire.get("approved_instruments", {})
	var library: Dictionary = instruments.get(instrument, {})
	var patterns := {}
	for section in manifest.rhythm_sequence:
		var levels: Dictionary = library.get(section.rhythm, {})
		if not levels.is_empty():
			var selected: Dictionary = levels.get(level, levels.values()[0])
			if selected.get("validation_status") == "approved":
				patterns[section.rhythm] = selected
	return patterns

func available_song_levels(entry: Dictionary, instrument: String) -> Dictionary:
	var library: Dictionary = local_repertoire.get("approved_instruments", {}).get(instrument, {})
	var by_rhythm := {}
	var levels := {}
	for section in entry.song.rhythm_sequence:
		var rhythm: String = section.rhythm
		if by_rhythm.has(rhythm):
			continue
		var supported := {}
		for level in library.get(rhythm, {}):
			var approved: Dictionary = library[rhythm][level]
			if approved.get("validation_status") == "approved":
				supported[level] = approved
		if instrument == "caixa" and entry.patterns.has(rhythm):
			var supplied: Dictionary = entry.patterns[rhythm]
			if (not public_repertoire or supplied.get("validation_status") == "approved") and not supported.has(supplied.difficulty):
				supported[supplied.difficulty] = supplied
		if supported.is_empty():
			return {}
		by_rhythm[rhythm] = supported
		for level in supported:
			levels[level] = true
	var choices := {}
	for level in LEVEL_NAMES:
		if levels.has(level) and by_rhythm.values().all(func(supported): return supported.has(level)):
			var selected := {}
			for rhythm in by_rhythm:
				selected[rhythm] = by_rhythm[rhythm][level]
			choices[level] = selected
	if choices.is_empty() and not by_rhythm.is_empty():
		var mixed := {}
		for rhythm in by_rhythm:
			var supported: Dictionary = by_rhythm[rhythm]
			mixed[rhythm] = supported.get("beginner", supported.values()[0])
		choices["mixed"] = mixed
	return choices

func select_song_level(level: String) -> void:
	difficulty = level
	local_patterns = local_level_choices[level]

func can_play_instrument(manifest: Dictionary, instrument: String) -> bool:
	if instrument == "caixa":
		return true
	var known := instrument_patterns(manifest, instrument, "beginner")
	return not known.is_empty() and manifest.rhythm_sequence.all(func(section): return known.has(section.rhythm))

func available_instrument(instrument: String) -> bool:
	if mode == "Aprender":
		return local_repertoire.get("approved_instruments", {}).has(instrument)
	for entry in local_catalog.values():
		if (mode != "Transições" or entry.song.rhythm_sequence.size() > 1) and can_play_instrument(entry.song, instrument):
			return true
	return false

func select_mode(value: String) -> void:
	mode = value
	practice_instrument = "caixa"
	local_practice = false
	section_choice = 0
	transition_choice = 1
	repeat_practice = false
	experimental = false
	screen("Instrumento")
	button("Caixa de guerra", select_content)
	var added := false
	for id in INSTRUMENT_NAMES:
		if id != "caixa" and available_instrument(id):
			button(INSTRUMENT_NAMES[id], func(): practice_instrument = id; select_content())
			added = true
	if not added:
		label("Repique e surdos aguardam mapas.")
	button("Voltar", home)

func select_content() -> void:
	section_choice = 0
	transition_choice = 1
	screen("Ritmo" if mode == "Aprender" else "Música")
	if not local_repertoire.is_empty():
		show_local_repertoire()
		button("Voltar", home)
		return
	if mode == "Aprender":
		button("Cortejo A", func(): pattern = "cortejo_a"; select_difficulty())
		button("Cortejo B", func(): pattern = "cortejo_b"; select_difficulty())
	else:
		button("Cortejo de Neon", func(): experimental = false; select_difficulty())
		for id in local_catalog:
			var entry: Dictionary = local_catalog[id]
			if mode != "Transições" or entry.song.rhythm_sequence.size() > 1:
				button("%s • experimental" % entry.song.title, func():
					if await select_local(id):
						options())
		label("Bloco na Rua • áudio ausente")
	button("Voltar", home)

func show_local_repertoire() -> void:
	if mode == "Aprender":
		var database: Dictionary = local_repertoire.get("approved_instruments", {}).get(practice_instrument, {})
		for id in RHYTHM_NAMES:
			if database.has(id):
				button(RHYTHM_NAMES[id], func(): choose_practice_level(id, database[id]))
			elif practice_instrument == "caixa" and local_repertoire.patterns.has(id):
				button("%s • experimental" % RHYTHM_NAMES[id], func():
					start_local_practice(id, local_repertoire.patterns[id]))
		return
	for item in local_repertoire.songs:
		var entry: Dictionary = item
		if (local_catalog.has(entry.id) and (mode != "Transições" or entry.rhythm_sequence.size() > 1)
				and can_play_instrument(local_catalog[entry.id].song, practice_instrument)):
			var title: String = entry.title if public_repertoire else "%s • experimental" % entry.title
			button(title, func():
				if await select_local(entry.id):
					options())
		elif public_repertoire or practice_instrument != "caixa":
			continue
		elif entry.get("preview"):
			button("%s • ouvir" % entry.title, func(): preview_song(entry))
		else:
			label("%s • áudio ausente" % entry.title, 18)

func choose_practice_level(id: String, levels: Dictionary) -> void:
	screen(RHYTHM_NAMES[id])
	for level in levels:
		button(LEVEL_NAMES.get(level, level), func(): start_local_practice(id, levels[level]))
	button("Voltar", select_content)

func start_local_practice(id: String, selected: Dictionary) -> void:
	if selected.instrument != practice_instrument or (practice_instrument != "caixa" and selected.validation_status != "approved"):
		return
	pattern = id
	practice_pattern = selected
	local_practice = true
	difficulty = selected.difficulty
	if float(selected.get("reference_bpm", 0)) > 0:
		bpm = clampf(float(selected.reference_bpm), 60, 180)
	options()

func practice_sound() -> AudioStreamWAV:
	return practice_sounds[practice_instrument] if state != "calibrate" else snare

func preview_song(entry: Dictionary) -> void:
	var path := str(entry.preview) if OS.has_feature("web") else workspace.path_join(str(entry.preview))
	var stream := await private_stream(path)
	screen(entry.title)
	var names := PackedStringArray()
	for section in entry.rhythm_sequence:
		names.append(RHYTHM_NAMES[section.rhythm])
	label("Acompanhamento convertido" if entry.preview_arranged else "Gravação original", 19)
	if entry.rhythm_sequence.size() > 1:
		label("Ordem das levadas no repertório", 18)
		for i in range(0, names.size(), 4):
			label(" → ".join(names.slice(i, i + 4)), 18)
		label("Tempos das mudanças aguardam revisão.", 17)
	if stream:
		music.stream = stream
		button("Ouvir", func(): music.play())
		button("Parar", func(): music.stop())
	else:
		label("Áudio indisponível")
	button("Voltar", func(): music.stop(); select_content())

func select_difficulty() -> void:
	screen("Dificuldade")
	button("Iniciante", func(): difficulty = "beginner"; options())
	button("Intermediário", func(): difficulty = "intermediate"; options())
	button("Voltar", select_content)

func options() -> void:
	screen((local_song.title if public_repertoire else "%s • experimental" % local_song.title) if experimental else (RHYTHM_NAMES[pattern] if local_practice else mode))
	if experimental and local_level_choices.size() > 1:
		button("Dificuldade  " + LEVEL_NAMES[difficulty], func():
			screen("Dificuldade")
			for level in local_level_choices:
				button(LEVEL_NAMES[level], func(): select_song_level(level); options())
			button("Voltar", options))
	if mode == "Ensaio" or mode == "Apresentação":
		button("Modo: " + mode, func(): mode = "Apresentação" if mode == "Ensaio" else "Ensaio"; options())
	if mode == "Aprender":
		label("Ouça o pulso e acompanhe a grade.")
		button("Loop  " + ("ligado" if repeat_practice else "desligado"), func(): repeat_practice = not repeat_practice; options())
		button("BPM  −    %d" % bpm, func(): bpm = maxf(60, bpm - 4); options())
		button("BPM  +    %d" % bpm, func(): bpm = minf(180, bpm + 4); options())
	elif mode != "Apresentação":
		if not experimental or local_slow_audio:
			button("Velocidade  %d%%" % (speed * 100), func(): speed = .75 if speed == 1.0 else 1.0; options())
		var selected: Dictionary = local_song if experimental else song
		var sequence: Array = selected.rhythm_sequence
		if mode == "Ensaio" and sequence.size() > 1:
			var section_title: String = "Música inteira" if section_choice == 0 else RHYTHM_NAMES.get(sequence[section_choice - 1].rhythm, sequence[section_choice - 1].rhythm)
			button("Trecho  " + section_title, func(): section_choice = (section_choice + 1) % (sequence.size() + 1); options())
		if mode == "Transições" and sequence.size() > 1:
			var before: String = RHYTHM_NAMES.get(sequence[transition_choice - 1].rhythm, sequence[transition_choice - 1].rhythm)
			var after: String = RHYTHM_NAMES.get(sequence[transition_choice].rhythm, sequence[transition_choice].rhythm)
			var pairing := "%s → %s" % [before, after]
			if sequence.size() > 2:
				button("%s  (%d/%d)" % [pairing, transition_choice, sequence.size() - 1],
					func(): transition_choice = transition_choice % (sequence.size() - 1) + 1; options())
			else:
				label(pairing, 18)
		if mode == "Transições" or section_choice > 0:
			button("Loop  " + ("ligado" if repeat_practice else "desligado"), func(): repeat_practice = not repeat_practice; options())
	button("Começar", func(): begin())
	button("Voltar", select_content if experimental or local_practice else select_difficulty)

func save() -> void:
	prefs.set_value("controls", "offset", offset)
	prefs.set_value("controls", "keys", bind)
	prefs.set_value("controls", "vibration", vibration)
	prefs.set_value("controls", "window_scale", window_scale)
	prefs.save("user://fogonuhero.cfg")

func set_mixer_level(bus: String, percent: float) -> void:
	var level := clampf(percent, 0, 100)
	var index := AudioServer.get_bus_index(bus)
	if index < 0:
		return
	mixer_levels[bus] = level
	AudioServer.set_bus_volume_db(index, linear_to_db(maxf(.0001, level / 100.0)))
	AudioServer.set_bus_mute(index, is_zero_approx(level))
	prefs.set_value("audio", bus, level)

func format_mixer_level(bus: String, level: float) -> String:
	return "%s   %d%%" % [MIXER_LABELS[bus], roundi(level)]

func audio_settings() -> void:
	screen("Volumes")
	for bus in MIXER_LABELS:
		var description := Label.new()
		description.text = format_mixer_level(bus, mixer_levels[bus])
		description.add_theme_font_size_override("font_size", 18)
		menu.add_child(description)
		var slider := HSlider.new()
		slider.min_value = 0
		slider.max_value = 100
		slider.step = 5
		slider.value = mixer_levels[bus]
		slider.custom_minimum_size.y = 30
		slider.tooltip_text = MIXER_LABELS[bus]
		slider.value_changed.connect(func(level):
			set_mixer_level(bus, level)
			description.text = format_mixer_level(bus, level))
		slider.drag_ended.connect(func(changed):
			if changed:
				save())
		menu.add_child(slider)
	button("Restaurar volumes", func():
		for bus in MIXER_LABELS:
			set_mixer_level(bus, 100)
		save()
		audio_settings())
	button("Voltar", func(): save(); settings())

func settings() -> void:
	state = "menu"
	screen("Configurações")
	label("Compensação  %+.0f ms" % (offset * 1000))
	button("− 5 ms", func(): offset = maxf(-.4, offset - .005); save(); settings())
	button("+ 5 ms", func(): offset = minf(.4, offset + .005); save(); settings())
	for i in range(2):
		button("%s  %s" % ["Esquerda" if i == 0 else "Direita", OS.get_keycode_string(bind[i])],
			func(): rebinding = i; screen("Pressione uma tecla"); button("Cancelar", func(): rebinding = -1; settings()))
	button("Vibração  " + ("ligada" if vibration else "desligada"), func(): vibration = not vibration; save(); settings())
	button("Janelas de acerto  %d%%" % (window_scale * 100), func():
		window_scale = 1.2 if is_equal_approx(window_scale, 1.0) else (.85 if window_scale > 1.1 else 1.0)
		save()
		settings())
	button("Volumes", audio_settings)
	button("Calibrar por batidas", func(): begin(true))
	button("Voltar", home)

func update_rhythm() -> void:
	var id: String = active_song.rhythm_sequence[0].rhythm
	for section in active_song.rhythm_sequence:
		if section.start_time > maxf(shift, time):
			break
		id = section.rhythm
	var title: String = RHYTHM_NAMES.get(id, id)
	if title != rhythm_name:
		rhythm_name = title
		if OS.has_feature("web"):
			JavaScriptBridge.eval("if (document.getElementById('rhythm-status')) document.getElementById('rhythm-status').textContent = " + JSON.stringify(title), true)

func begin(calibrate := false) -> void:
	var practice := mode == "Aprender" or calibrate
	var local_play := experimental and not practice
	active_song = (local_song if local_play else song).duplicate(true)
	shift = 0.0
	var tempo := bpm if practice else float(active_song.bpm)
	if practice:
		active_song.id = "calibracao" if calibrate else "pratica"
		active_song.duration = (8 if calibrate else 16) * 60 / tempo
		active_song.tempo_map = [{"time": 0.0, "bpm": tempo}]
		active_song.rhythm_sequence = [{"start_time": 0.0, "rhythm": pattern}]
	elif mode == "Transições":
		var crossing: float = active_song.rhythm_sequence[transition_choice].start_time
		var previous_start: float = active_song.rhythm_sequence[transition_choice - 1].start_time
		shift = maxf(crossing - 4 * 60 / tempo, previous_start)
		var end := Chart.clock_time(active_song.tempo_map, crossing, 4)
		if transition_choice + 1 < active_song.rhythm_sequence.size():
			end = minf(end, active_song.rhythm_sequence[transition_choice + 1].start_time)
		active_song.duration = minf(active_song.duration, end)
		active_song.rhythm_sequence.resize(transition_choice + 1)
	elif mode == "Ensaio" and section_choice > 0:
		var section_index := section_choice - 1
		shift = active_song.rhythm_sequence[section_index].start_time
		if section_index + 1 < active_song.rhythm_sequence.size():
			active_song.duration = active_song.rhythm_sequence[section_index + 1].start_time
		active_song.rhythm_sequence.resize(section_index + 1)
	var slow := not practice and mode != "Apresentação" and speed < 1.0 and (not local_play or local_slow_audio != null)
	if slow:
		Chart.slow_timeline(active_song, speed)
		shift /= speed
		tempo *= speed
	var patterns := {}
	if not public_repertoire:
		for id in ["cortejo_a", "cortejo_b"]:
			patterns[id] = Chart.read("res://data/rhythms/caixa/%s_%s.json" % [id, difficulty])
	if local_play:
		patterns = local_patterns
	elif local_practice and not calibrate:
		patterns = {pattern: practice_pattern}
		active_song.id = "%s_%s" % [practice_instrument, pattern]
	chart = Chart.generate(active_song, patterns, (local_play and not public_repertoire) or (local_practice and practice_instrument == "caixa" and not public_repertoire)).filter(func(note): return note.time >= shift)
	ensemble_layers.clear()
	if local_play:
		for instrument in INSTRUMENT_NAMES:
			if instrument == practice_instrument:
				continue
			var backing := instrument_patterns(active_song, instrument, difficulty)
			if backing.is_empty():
				continue
			var notes := Chart.generate(active_song, backing, false, true).filter(func(note): return note.time >= shift)
			if not notes.is_empty():
				ensemble_layers[instrument] = {"events": notes, "cursor": 0}
	score = Score.new()
	match difficulty:
		"advanced":
			windows = [.030, .060, .105]
		"intermediate":
			windows = [.038, .076, .126]
		_:
			windows = [.045, .090, .150]
	windows = windows.map(func(seconds): return seconds * window_scale)
	banner = ""
	clock = SongClock.new()
	clock.last = shift
	music.stop()
	if practice:
		music.stream = practice_track(tempo, active_song.duration)
	elif local_play:
		music.stream = local_slow_audio if slow else local_audio
	else:
		music.stream = load(DEMO_AUDIO[int(slow)])
	next_beat = shift
	next_ensemble = shift
	next_kit = 0
	next_miss = 0
	countdown_tick = -4
	calibration.clear()
	pointers.clear()
	time = shift - 3 * 60 / tempo * music.pitch_scale
	start_at = Time.get_ticks_msec() + roundi(3000 * 60 / tempo)
	last_audio_advance = start_at
	state = "calibrate" if calibrate else "play"
	rhythm_name = ""
	if not calibrate:
		update_rhythm()
	web_status("Calibrar" if calibrate else "Partida")
	if OS.has_feature("web"):
		JavaScriptBridge.eval("document.documentElement.dataset.gamePhase = 'countdown'")
	menu.hide()

func practice_track(tempo: float, duration: float) -> AudioStreamWAV:
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = click.mix_rate
	var data := PackedByteArray()
	data.resize(roundi(duration * stream.mix_rate) * 2)
	var pulse := click.data
	for beat in range(ceili(duration * tempo / 60)):
		var start := roundi(beat * 60 / tempo * stream.mix_rate) * 2
		for i in range(mini(pulse.size(), data.size() - start)):
			data[start + i] = pulse[i]
	stream.data = data
	return stream

func play_ensemble(moment: float) -> void:
	for instrument in ensemble_layers:
		var layer: Dictionary = ensemble_layers[instrument]
		while layer.cursor < layer.events.size() and layer.events[layer.cursor].time <= moment:
			var note: Dictionary = layer.events[layer.cursor]
			play_hit(instrument_voices[instrument], practice_sounds[instrument], -16 if note.accent else -23)
			layer.cursor += 1

func play_virtual_battery(moment: float) -> void:
	play_ensemble(moment)
	if mode == "Apresentação":
		return
	while next_kit < chart.size() and chart[next_kit].time <= moment:
		var note: Dictionary = chart[next_kit]
		play_hit(instrument_voices[practice_instrument], practice_sound(), -15 if note.accent else -23)
		next_kit += 1

func _process(_delta: float) -> void:
	if state in ["play", "calibrate"]:
		var wall := Time.get_ticks_msec()
		var tempo: float = active_song.tempo_map[0].bpm
		if wall < start_at:
			time = shift + (wall - start_at) / 1000.0 * music.pitch_scale
			var tick := floori((wall - start_at) / 1000.0 * tempo / 60.0)
			if tick != countdown_tick:
				play_hit(3, click, -9)
				countdown_tick = tick
		elif not music.playing and time < shift:
			time = shift
			music.play(shift)
			if OS.has_feature("web"):
				JavaScriptBridge.eval("document.documentElement.dataset.gamePhase = 'playing'")
		elif music.playing:
			var moment: float = clock.read(music)
			if moment > time:
				last_audio_advance = wall
			elif wall - last_audio_advance > 3500:
				pause("Áudio suspenso. Toque em Continuar.")
				return
			time = moment
		else:
			time = active_song.duration
		if state == "play":
			update_rhythm()
		if time >= shift:
			if state == "play":
				expire_notes(time - offset * music.pitch_scale)
				if mode != "Aprender" and not experimental:
					var half_beat := 30.0 / tempo
					while next_ensemble <= time and next_ensemble < active_song.duration:
						var pulse := roundi((next_ensemble - shift) / half_beat)
						if pulse % 4 == 0:
							play_hit(4, surdo, -12)
						elif pulse % 4 == 3:
							play_hit(5, repique, -22)
						next_ensemble += half_beat
				play_virtual_battery(time)
			if time >= active_song.duration:
				var loops := mode in ["Aprender", "Transições"] or (mode == "Ensaio" and section_choice > 0)
				if state == "play" and loops and repeat_practice:
					begin()
				else:
					results()
	queue_redraw()

func pause(message := "") -> void:
	if state not in ["play", "calibrate"]:
		return
	var previous := state
	state = "paused"
	paused_at = Time.get_ticks_msec()
	music.stream_paused = true
	pointers.clear()
	screen("Pausa")
	if not message.is_empty():
		label(message, 19)
	button("Continuar", func():
		start_at += Time.get_ticks_msec() - paused_at
		last_audio_advance = Time.get_ticks_msec()
		music.stream_paused = false
		state = previous
		web_status("Calibrar" if previous == "calibrate" else "Partida")
		menu.hide())
	button("Reiniciar", func(): music.stream_paused = false; begin(previous == "calibrate"))
	button("Menu", func(): music.stream_paused = false; home())

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT and is_instance_valid(menu):
		pause()

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if rebinding >= 0 and event.physical_keycode not in [KEY_ESCAPE, bind[1 - rebinding]]:
			bind[rebinding] = event.physical_keycode
			rebinding = -1
			save()
			settings()
		elif state in ["play", "calibrate"]:
			if event.physical_keycode == KEY_ESCAPE:
				pause()
			elif event.physical_keycode in bind:
				strike(bind.find(event.physical_keycode))
	if state not in ["play", "calibrate"]:
		return
	if event is InputEventScreenTouch:
		if event.pressed and not pointers.has(event.index):
			pointers[event.index] = true
			touch(event.position)
		elif not event.pressed:
			pointers.erase(event.index)
	elif event is InputEventMouseButton and event.device != InputEvent.DEVICE_ID_EMULATION and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		touch(event.position)

func touch(position: Vector2) -> void:
	if position.y < 85:
		pause()
	elif position.y > size.y * .71:
		strike(0 if position.x < size.x / 2 else 1)

func expire_notes(moment: float) -> void:
	var threshold: float = moment - windows[2] * music.pitch_scale
	while next_miss < chart.size() and chart[next_miss].time < threshold:
		var note: Dictionary = chart[next_miss]
		if not note.done:
			score.record(note, 0)
		next_miss += 1

func strike(lane: int) -> void:
	flash[lane] = Time.get_ticks_msec() + 110
	play_hit(lane, practice_sound(), -5)
	if vibration:
		Input.vibrate_handheld(24)
	if time < shift:
		return
	if state == "calibrate":
		var period: float = 60 / active_song.tempo_map[0].bpm
		var error := clock.read(music) - snappedf(clock.last, period)
		if absf(error) < .23 and roundi(clock.last / period) >= next_beat:
			calibration.append(error)
			next_beat = roundi(clock.last / period) + 1
		return
	var moment: float = clock.read(music) - offset * music.pitch_scale
	expire_notes(moment)
	var selected := {}
	var best_error := INF
	var span: float = windows[2] * music.pitch_scale
	var first := Chart.first_at_or_after(chart, moment - span)
	for i in range(first, chart.size()):
		var note: Dictionary = chart[i]
		if note.time > moment + span:
			break
		if note.done or note.hand not in ["unknown", "left" if lane == 0 else "right"]:
			continue
		var error: float = absf(moment - note.time) / music.pitch_scale
		if error < best_error:
			best_error = error
			selected = note
	var grade := Score.judge(best_error, windows)
	if grade:
		score.record(selected, grade)
		banner = ["", "Bom", "Ótimo", "Perfeito"][grade]
	else:
		score.extra_hit()
		banner = "Fora do tempo"

func results() -> void:
	music.stop()
	if state == "calibrate":
		state = "menu"
		var updated := calibration.size() >= 3
		if updated:
			calibration.sort()
			offset = calibration[floori(calibration.size() / 2.0)]
			save()
		screen("Calibração")
		label("Compensação  %+.0f ms" % (offset * 1000) if updated else "Toque em pelo menos três pulsos.")
		button("Repetir", func(): begin(true))
		button("Configurações", settings)
		return
	state = "results"
	for note in chart:
		if not note.done:
			score.record(note, 0)
	var high_key := "%s_%s_%s" % [active_song.id, mode, difficulty]
	if practice_instrument != "caixa":
		high_key += "_" + practice_instrument
	prefs.set_value("records", high_key, maxi(score.points, prefs.get_value("records", high_key, 0)))
	save()
	screen("Resultado")
	var rating := "S" if score.accuracy() >= 95 else ("A" if score.accuracy() >= 80 else ("B" if score.accuracy() >= 60 else "C"))
	label("%s   •   %d pontos   •   %.1f%%" % [rating, score.points, score.accuracy()])
	label("Combo máximo %d   •   Erros %d" % [score.best, score.misses])
	for field in [score.by_hand, score.by_rhythm]:
		for id in field:
			var total: Vector2 = field[id]
			var hands := {"left": "Esquerda", "right": "Direita", "unknown": "Mão a identificar"}
			var title: String = hands.get(id, RHYTHM_NAMES.get(id, id))
			label("%s   %.0f%%" % [title, total.x * 100 / total.y], 17)
	button("Repetir", func(): begin())
	button("Menu", home)

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color("#16132e"))
	for i in range(34):
		var x := fmod(i * 79.0, size.x)
		var y := fmod(i * 113.0, size.y)
		draw_rect(Rect2(x, y, 5, 8), COLORS[i % 2].darkened(.65))
	for i in range(20):
		var x := i * size.x / 20
		draw_colored_polygon(PackedVector2Array([Vector2(x, 10), Vector2(x + size.x / 23, 10),
			Vector2(x + size.x / 46, 38)]), COLORS[i % 2])
	if state not in ["play", "calibrate"]:
		var reel := int(Time.get_ticks_msec() / 230.0) % 2
		var actor := Vector2(size.x / 2 - 34, size.y - 130)
		draw_rect(Rect2(actor + Vector2(18, 0), Vector2(32, 22)), Color("#d79b70"))
		draw_rect(Rect2(actor + Vector2(14, -6), Vector2(40, 10)), Color("#594780"))
		draw_rect(Rect2(actor + Vector2(9, 22), Vector2(50, 38)), COLORS[0])
		draw_rect(Rect2(actor + Vector2(0, 41), Vector2(68, 29)), Color("#bb416e"))
		draw_rect(Rect2(actor + Vector2(0, 39), Vector2(68, 7)), Color("#ffe073"))
		for arm in range(2):
			var x := 6 + arm * 50
			var y := 20 - 12 * ((reel + arm) % 2)
			draw_rect(Rect2(actor + Vector2(x, y), Vector2(7, 27)), Color("#d79b70"))
		return
	var font := ThemeDB.fallback_font
	var width := minf(size.x, 560)
	var edge := (size.x - width) / 2
	var line := size.y * .76
	var lane_width := width / 2
	for i in range(2):
		var x := edge + i * lane_width
		draw_rect(Rect2(x + 3, 174, lane_width - 6, size.y - 178), Color("#242040"))
		var color: Color = COLORS[i]
		draw_rect(Rect2(x + 3, line, lane_width - 6, size.y - line - 4),
			color if Time.get_ticks_msec() < flash[i] else color.darkened(.55))
		draw_string(font, Vector2(x + 12, line + 52), ("ESQUERDA" if i == 0 else "DIREITA") +
			"  " + OS.get_keycode_string(bind[i]), HORIZONTAL_ALIGNMENT_LEFT, -1, 21)
	draw_line(Vector2(edge, line), Vector2(edge + width, line), Color.WHITE, 4)
	if state == "play":
		var first := Chart.first_at_or_after(chart, time - .2 * music.pitch_scale)
		for i in range(first, chart.size()):
			var note: Dictionary = chart[i]
			var distance: float = (note.time - time) / music.pitch_scale
			if distance > 2:
				break
			if note.done:
				continue
			var lane := 0 if note.hand == "left" else 1
			var y := line - distance * (line - 185) / 2
			var rect := Rect2(edge + lane * lane_width + 16, y - 8, lane_width - 32, 16)
			if note.hand == "unknown":
				rect.position.x = size.x / 2 - rect.size.x / 2
			draw_rect(rect, Color("#c8bce4") if note.hand == "unknown" else COLORS[lane])
			if note.accent:
				draw_rect(rect.grow(3), Color("#ffe073"), false, 3)
	var title := "PAUSA   %d pts   Combo %d   ×%d" % [score.points, score.combo, score.multiplier()]
	if state == "calibrate":
		title = "PAUSA    Toque a cada pulso   %d/8" % calibration.size()
	draw_string(font, Vector2(edge + 10, 78), title, HORIZONTAL_ALIGNMENT_LEFT, -1, 24)
	var header := Rect2(edge + 3, 94, width - 6, 72)
	draw_rect(header, Color("#302951"))
	draw_rect(Rect2(header.position, Vector2(4, header.size.y)), Color("#ffe073"))
	var caption := "RITMO ATUAL" if state == "play" else "CALIBRAÇÃO"
	var rhythm := rhythm_name if state == "play" else "Metrônomo"
	if state == "play" and ((experimental and not public_repertoire) or (local_practice and practice_pattern.validation_status != "approved")):
		caption += " · EXPERIMENTAL"
	elif state == "play" and (local_practice or experimental):
		caption += " · " + INSTRUMENT_NAMES[practice_instrument]
	draw_string(font, Vector2(edge + 20, 118), caption, HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color("#e4d9fa"))
	draw_string(font, Vector2(edge + 20, 151), rhythm, HORIZONTAL_ALIGNMENT_LEFT, -1, 30, Color("#ffe073"))
	var feedback := banner if state == "play" else ""
	if time < shift:
		var count := maxi(1, ceili((start_at - Time.get_ticks_msec()) / 1000.0 * active_song.tempo_map[0].bpm / 60))
		feedback = "Começa em %d" % count
	draw_string(font, Vector2(edge + width * .53, 147), feedback, HORIZONTAL_ALIGNMENT_RIGHT, width * .43, 20)
