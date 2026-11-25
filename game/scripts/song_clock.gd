extends RefCounted

var last := 0.0

func read(player: AudioStreamPlayer) -> float:
	if player.playing and not player.stream_paused:
		var interpolation := -AudioServer.get_output_latency()
		if player.playback_type != AudioServer.PLAYBACK_TYPE_SAMPLE:
			interpolation += AudioServer.get_time_since_last_mix()
		last = maxf(last, player.get_playback_position() + interpolation * player.pitch_scale)
	return last
