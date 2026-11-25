import copy
import json
import tempfile
import shutil
import unittest
from pathlib import Path

from build_repertoire import checksum, pattern_checksum, release_plan
from index_local_repertoire import approved_pattern
from prepare_playtest import apply_review, prepare
from validate_assets import PATTERNS, ROOT, validate, validate_pattern


class PublicationTest(unittest.TestCase):
    def test_public_manifest(self):
        validate(ROOT / "game")

    def test_rejects_draft_and_out_of_bounds_note(self):
        pattern = json.loads((ROOT / "game" / PATTERNS[0]).read_text())
        for change in ("draft", "bounds"):
            edited = copy.deepcopy(pattern)
            if change == "draft":
                edited["validation_status"] = "draft"
            else:
                edited["notes"][-1]["beat"] = edited["loop_beats"]
            with self.assertRaises(ValueError):
                validate_pattern(edited)

    def test_rejects_audio_replacement_at_authorized_path(self):
        with tempfile.TemporaryDirectory() as empty:
            game = Path(empty)
            shutil.copytree(ROOT / "game/data", game / "data")
            (game / "assets").mkdir()
            (game / "assets/cortejo.ogg").write_bytes(b"OggSreplace")
            with self.assertRaisesRegex(ValueError, "fora da autorização"):
                validate(game)

    def test_missing_files(self):
        with tempfile.TemporaryDirectory() as empty:
            game = Path(empty)
            shutil.copytree(ROOT / "game/data", game / "data")
            with self.assertRaises(FileNotFoundError) as error:
                validate(game)
            self.assertEqual(Path(error.exception.filename).name, "cortejo.ogg")


class RepertoireReleaseTest(unittest.TestCase):
    def test_exports_only_approved_arrangement_and_sanitizes_patterns(self):
        pattern = json.loads((ROOT / "game" / PATTERNS[0]).read_text())
        pattern.update(id="fixture_pattern", rhythm="samba", validation_status="approved",
                       reference_sha256="private reference")
        pattern["notes"][0]["internal"] = "private note"
        song = {"id": "fixture", "title": "Faixa de teste", "bpm": 110, "duration": 12,
                "tempo_map": [{"time": 0, "bpm": 110}], "rhythm_timing_status": "approved",
                "rhythm_sequence": [{"rhythm": "samba", "start_time": 0}], "audio": "accompaniment.ogg"}
        repertoire = {"songs": [song], "approved_instruments": {"caixa": {"samba": {"beginner": pattern}}}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = root / "fixture"
            session.mkdir()
            (session / "song.json").write_text(json.dumps(song))
            audio = session / "accompaniment.ogg"
            audio.write_bytes(b"OggS fixture")
            rights = {"repertoire": {"fixture": {"authorized": True, "license": "TEST",
                       "permission_reference": "test", "sha256": checksum(audio)}}}
            with self.assertRaisesRegex(ValueError, "Mapa de caixa"):
                release_plan(rights, repertoire, root, root, {"fixture": ["samba"]})
            rights["patterns"] = {pattern["id"]: {"authorized": True, "license": "TEST",
                                  "permission_reference": "test", "sha256": pattern_checksum(pattern)}}
            catalogue, assets = release_plan(rights, repertoire, root, root, {"fixture": ["samba"]})
            self.assertEqual(assets, {"audio/fixture.ogg": audio})
            serialized = json.dumps(catalogue)
            self.assertNotIn("private", serialized)
            self.assertNotIn("accompaniment.ogg", serialized)
            audio.write_bytes(b"OggS other bytes")
            with self.assertRaisesRegex(ValueError, "diverge"):
                release_plan(rights, repertoire, root, root, {"fixture": ["samba"]})


class PlaytestTest(unittest.TestCase):
    def test_instrument_map_requires_approved_video_identity(self):
        pattern = json.loads((ROOT / "game" / PATTERNS[0]).read_text())
        pattern.update(id="repique_test", rhythm="ijexa", instrument="repique",
                       validation_status="draft", reference_sha256="video")
        candidates = [(copy.deepcopy(pattern), "video")]
        with self.assertRaisesRegex(ValueError, "Aprove"):
            approved_pattern(pattern, candidates)
        pattern["validation_status"] = "approved"
        with self.assertRaisesRegex(ValueError, "técnica"):
            approved_pattern(pattern, candidates)
        for note in pattern["notes"]:
            note["technique"] = "stroke"
        self.assertEqual(approved_pattern(pattern, candidates), pattern)
        pattern["reference_sha256"] = "other"
        with self.assertRaisesRegex(ValueError, "vídeo"):
            approved_pattern(pattern, candidates)

    def test_import_approved_timings_for_same_recording(self):
        song = {"id": "eva", "duration": 20, "analysis": {"sha256": "source"},
                "rhythm_sequence": [{"rhythm": "ijexa", "start_time": None},
                                    {"rhythm": "samba_reggae", "start_time": None}]}
        review = copy.deepcopy(song)
        review["rhythm_sequence"][0]["start_time"] = .36
        review["rhythm_sequence"][1]["start_time"] = 8.47
        with self.assertRaisesRegex(ValueError, "Aprove"):
            apply_review(song, review)
        review["validation_status"] = "approved"
        result = apply_review(song, review)
        self.assertEqual(result["rhythm_sequence"], review["rhythm_sequence"])
        self.assertEqual(result["rhythm_timing_status"], "approved")
        self.assertIsNone(song["rhythm_sequence"][0]["start_time"])
        review["rhythm_sequence"][1]["start_time"] = float("nan")
        with self.assertRaisesRegex(ValueError, "instantes"):
            apply_review(song, review)
        review["rhythm_sequence"].reverse()
        with self.assertRaisesRegex(ValueError, "sequência"):
            apply_review(song, review)
        review["analysis"]["sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "gravação"):
            apply_review(song, review)

    def test_transition_order_and_review(self):
        sequence = [{"rhythm": "ijexa", "start_time": 0}, {"rhythm": "samba", "start_time": None},
                    {"rhythm": "ijexa", "start_time": 8.75}]
        song = {"rhythm_sequence": sequence, "analysis": {"sha256": "same"}}
        report = {"duration": 12.0, "source_sha256": "same", "bpm_estimate": 110, "key_estimate": None}
        patterns = {rhythm: {"instrument": "caixa", "loop_beats": 2, "difficulty": "beginner",
                             "notes": [{"beat": 0, "hand": "unknown"}]} for rhythm in ("ijexa", "samba")}
        with self.assertRaisesRegex(ValueError, "transições"):
            prepare(song, report, patterns)
        sequence[1]["start_time"] = 3.25
        result = prepare(song, report, patterns)
        self.assertEqual(result["rhythm_sequence"], sequence)
        self.assertEqual(result["validation_status"], "draft")
        report["source_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "corresponder"):
            prepare(song, report, patterns)


if __name__ == "__main__":
    unittest.main()
