"""Index estimates for available songs and caixa references."""
import argparse
import json
import unicodedata

from analyze import analyze
from catalog_assets import LOCAL, MOVIES, ORDERS, ROOT, save
from midi_arrangement import tempo_events

RHYTHMS = {"ijexa": "ijexa", "samba": "samba", "samba reggae": "samba_reggae",
           "xote _ baiao": "baiao_xote", "marchinha": "marchinha", "maracatu": "maracatu",
           "rumba": "rumba", "maculele": "maculele"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["songs", "caixa", "ensemble"])
    args = parser.parse_args()
    index = {}
    if args.only in (None, "songs"):
        for ident, (_, name, _, _, _) in ORDERS.items():
            file = ROOT / "musicas" / (name or "")
            if file.is_file():
                directory = analyze(file)
                index[ident] = str(directory.relative_to(LOCAL))
                manifest = LOCAL / "songs" / f"{ident}.json"
                if manifest.is_file():
                    song = json.loads(manifest.read_text())
                    data = json.loads((directory / "analysis.json").read_text())
                    song["analysis"] = {
                        "status": "estimate", "sha256": data["sha256"], "report": index[ident] + "/analysis.json",
                        "bpm": data["bpm"], "key": data["key_estimate"],
                        "tempo_map": [dict(time=t, bpm=60000000 / us)
                                      for t, us in tempo_events(data["beats"], data["bpm"] or 120)],
                    }
                    save(manifest, song)
    if args.only in (None, "caixa"):
        for file in sorted((MOVIES / "Caixa").glob("*.mp4")):
            rhythm = file.stem.split(" - ")[0].lower()
            rhythm = unicodedata.normalize("NFKD", rhythm).encode("ascii", "ignore").decode()
            if rhythm in RHYTHMS and "(comentários)" not in file.name:
                level = "beginner" if "(iniciante)" in file.name else "unspecified"
                index[file.name] = str(analyze(file, RHYTHMS[rhythm], level).relative_to(LOCAL))
    if args.only == "ensemble":
        instruments = {"Repique": "repique", "Surdo de Primeira": "surdo_primeira",
                       "Surdo de Segunda": "surdo_segunda", "Surdo de Terceira": "surdo_terceira",
                       "Surdo de Marcação": "surdo_marcacao"}
        for folder in ("Repiques", "Surdos"):
            for file in sorted((MOVIES / folder).glob("*.mp4")):
                title, _, label = file.stem.partition(" - ")
                plain = unicodedata.normalize("NFKD", title.lower()).encode("ascii", "ignore").decode()
                rhythm = RHYTHMS.get(plain.replace("baiao _ xote", "xote _ baiao"))
                instrument = instruments.get(label.split("(")[0].strip())
                if rhythm and instrument:
                    level = "beginner" if "(iniciante)" in file.name else "unspecified"
                    index[file.name] = str(analyze(file, rhythm, level, instrument).relative_to(LOCAL))
    save(LOCAL / f"analysis-index-{args.only or 'all'}.json", index)


if __name__ == "__main__":
    main()
