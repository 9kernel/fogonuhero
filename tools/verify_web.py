"""Validate the Web artifact and every resource path in the Godot 4.5 PCK index."""
from pathlib import Path
import re
import struct
import sys

from validate_assets import DEMO_AUDIO, PATTERNS

WEB_FILES = ("index.html", "index.js", "index.wasm", "index.pck", "index.audio.worklet.js",
             "index.audio.position.worklet.js", "app.js", "styles.css", "GODOT-NOTICES.txt")
COMMON_RESOURCES = {
    "main.tscn.remap", "project.binary",
    ".godot/global_script_class_cache.cfg", ".godot/uid_cache.bin",
    *(f"scripts/{name}.{suffix}" for name in ("chart", "main", "score", "song_clock")
      for suffix in ("gd.remap", "gdc")),
}
FIXED_RESOURCES = COMMON_RESOURCES | {*(name + ".import" for name in DEMO_AUDIO),
                                      "data/songs/cortejo.json", *PATTERNS}
SCENE = re.compile(r"\.godot/exported/\d+/export-[0-9a-f]{32}-main\.scn")
IMPORTED = re.compile(r"\.godot/(?:imported/cortejo(?:_075)?\.ogg-[0-9a-f]{32}\.oggvorbisstr"
                      r"|exported/\d+/export-[0-9a-f]{32}-main\.scn)")


def pack_paths(data):
    if data[:8] != b"GDPC\x03\x00\x00\x00":
        raise ValueError("Formato PCK")
    pos, = struct.unpack_from("<Q", data, 32)
    count, = struct.unpack_from("<I", data, pos)
    pos += 4
    names = set()
    for _ in range(count):
        size, = struct.unpack_from("<I", data, pos)
        pos += 4
        name = data[pos:pos + size].rstrip(b"\x00").decode()
        if name in names:
            raise ValueError(f"Recurso duplicado no PCK: {name}")
        names.add(name)
        pos += size + 36
    if pos != len(data):
        raise ValueError("Índice PCK incompleto")
    return names


def verify(path, repertoire=False):
    for name in WEB_FILES:
        if not (path / name).stat().st_size:
            raise ValueError(name)
    with (path / "index.wasm").open("rb") as stream:
        if stream.read(8) != b"\0asm\x01\0\0\0":
            raise ValueError("WebAssembly")
    names = pack_paths((path / "index.pck").read_bytes())
    if repertoire:
        if not COMMON_RESOURCES <= names or len(names - COMMON_RESOURCES) != 1 or not all(
                SCENE.fullmatch(name) for name in names - COMMON_RESOURCES):
            raise ValueError("O PCK do repertório só pode conter o motor do jogo e a cena principal")
        return
    unknown = {name for name in names - FIXED_RESOURCES if not IMPORTED.fullmatch(name)}
    if unknown or not FIXED_RESOURCES <= names or len(names) != len(FIXED_RESOURCES) + len(DEMO_AUDIO) + 1:
        raise ValueError(f"Recursos PCK inesperados: {sorted(unknown)}")


if __name__ == "__main__":
    target = Path(sys.argv[1])
    verify(target, repertoire="--repertoire" in sys.argv)
    if "--strict" in sys.argv and {item.name for item in target.iterdir()} != set(WEB_FILES):
        raise ValueError("Arquivos excedentes na pasta de publicação")
