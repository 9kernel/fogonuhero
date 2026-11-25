"""Convert every available catalog recording locally, preserving per-song logs."""
import argparse
from pathlib import Path
import subprocess
import sys

from catalog_assets import LOCAL, ORDERS, ROOT, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tunerize", type=Path, required=True)
    parser.add_argument("--song", action="append", choices=ORDERS)
    args = parser.parse_args()
    destination = LOCAL / "conversion-logs"
    destination.mkdir(parents=True, exist_ok=True)
    statuses = {}
    failed = False
    for ident, (_, name, _, _, _) in ORDERS.items():
        if args.song and ident not in args.song:
            continue
        source = ROOT / "musicas" / (name or "")
        if not source.is_file():
            statuses[ident] = "missing_source"
            continue
        print(f"Convertendo {ident}", flush=True)
        logfile = destination / f"{ident}.log"
        with logfile.open("w", encoding="utf-8") as output:
            process = subprocess.run([sys.executable, str(ROOT / "tools/convert_chiptune.py"),
                                      str(source), "--tunerize", str(args.tunerize)],
                                     stdout=output, stderr=subprocess.STDOUT)
        statuses[ident] = "failed" if process.returncode else "ready_for_review"
        failed |= process.returncode != 0
        save(destination / "summary.json", statuses)
    save(destination / "summary.json", statuses)
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
