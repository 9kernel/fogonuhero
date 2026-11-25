"""Inventory only local sources; never copy source media into the game."""
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
MOVIES = ROOT / "Levadas da Percussão 2026"
ORDERS = {
    "bloco_na_rua": ("Bloco na Rua", None, None, "Cm", "ijexa samba ijexa samba"),
    "vou_festejar": ("Vou Festejar", "Vou Festejar.mp3", None, None, "samba"),
    "eva": ("Eva", "Eva (Eva) (Ao Vivo).mp3", None, "Bb", "ijexa samba_reggae ijexa samba_reggae ijexa samba_reggae"),
    "lucro": ("Lucro", "BaianaSystem - Lucro (Descomprimindo).mp3", "BaianaSystem", "C",
              "maracatu rumba maracatu samba_reggae maracatu rumba maracatu samba_reggae ijexa maracatu"),
    "vermelho": ("Vermelho", "Vermelho.mp3", None, "A", "baiao_xote samba_reggae baiao_xote samba_reggae"),
    "bella_ciao": ("Bella Ciao", "Bella Ciao - Modena City Ramblers.mp3", "Modena City Ramblers", None, "maculele"),
    "alalao": ("Alalaô", "Alalaô.mp3", None, None, "marchinha"),
}


def probe(file):
    result = subprocess.check_output(["ffprobe", "-v", "error", "-show_format",
                                      "-show_streams", "-of", "json", str(file)])
    return json.loads(result)


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False)
    name = Path(temp.name)
    try:
        with temp:
            json.dump(data, temp, indent=2, ensure_ascii=False, allow_nan=False)
            temp.write("\n")
        name.replace(path)
    finally:
        name.unlink(missing_ok=True)



def main():
    rows = []
    info = {}
    for directory in (ROOT / "musicas", MOVIES):
        for file in sorted(p for p in directory.rglob("*") if p.is_file()):
            relative = file.relative_to(ROOT).as_posix()
            data = probe(file)
            data["format"]["filename"] = relative
            info[relative] = data
            audio = next(s for s in data["streams"] if s["codec_type"] == "audio")
            video = next((s for s in data["streams"] if s["codec_type"] == "video" and not s["disposition"]["attached_pic"]), {})
            rhythm, _, instrument = file.stem.partition(" - ")
            level = next((x for x in ("iniciante", "avançado") if f"({x})" in instrument), "—")
            instrument = instrument.split("(")[0].strip()
            rows.append(f"| {file.name} | {(instrument if video else '') or '—'} | {rhythm if video else '—'} | {level} | "
                        f"{float(data['format']['duration']):.2f} | "
                        f"{audio['codec_name']} / {audio['sample_rate']} / {audio['channels']} | "
                        + (f"{video['codec_name']} {video['width']}×{video['height']} @ {video['avg_frame_rate']}" if video else "—") + " |")
    save(LOCAL / "inventory.json", info)
    for ident, (title, name, artist, key, sequence) in ORDERS.items():
        source = f"musicas/{name}" if name else None
        metadata = info.get(source, {})
        tags = {k.lower(): v for k, v in metadata.get("format", {}).get("tags", {}).items()}
        save(LOCAL / "songs" / f"{ident}.json", dict(
            id=ident, title=title, artist=artist or tags.get("artist"), source=source,
            source_available=bool(metadata), key_original=None, key_target=key, bpm=None,
            tempo_map=[], duration=float(metadata["format"]["duration"]) if metadata else None,
            audio=None, instruments=[], difficulties=[],
            rhythm_sequence=[dict(rhythm=r, start_time=None) for r in sequence.split()],
            validation_status="draft", license="pending", distribution=False))
    (ROOT / "docs/ASSET_INVENTORY.md").write_text(
        "# Inventário de referências locais\n\n"
        "Mídias inspecionadas com FFprobe. A coluna de dificuldade registra o rótulo do arquivo. "
        "Variantes e indicações de velocidade constam no nome. Dados completos ficam em `.local/inventory.json`.\n\n"
        "Bloco na Rua consta em notas.md sem gravação no acervo. As notas dão a ordem das levadas "
        "e incluem também «Lula», com marchinha e sem gravação identificada. As notas não fornecem timestamps.\n\n"
        "| Arquivo | Instrumento no nome | Ritmo ou exercício | Dificuldade | Segundos | Áudio: codec / Hz / canais | Vídeo |\n"
        "|---|---|---|---|---:|---|---|\n" + "\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
