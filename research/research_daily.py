"""Daily Creamer research job (Windows task FuturesBotResearchDaily, runs hidden).

1. fetch_transcripts.py --daily : one request; if YouTube still blocks, stop for today.
2. extract_knowledge.py        : notes for any transcript without notes yet (Claude API).
3. synthesize.py               : rebuild creamer_knowledge.md when all teaching videos
                                 (+ the IQCapital interview) have notes and new notes
                                 arrived since the last build.
When every video, short and stream has notes and the final synthesis is done, it writes
research/ALL_DONE and later runs exit immediately. Log: research/daily_log.txt.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = HERE.parent / ".venv" / "Scripts" / "python.exe"
LOG = HERE / "daily_log.txt"
NO_WINDOW = 0x08000000  # never flash a console (owner games full-screen)


def log(msg: str) -> None:
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M} {msg}\n")


def run(script: str, *args: str) -> int:
    r = subprocess.run([str(PY), str(HERE / script), *args], cwd=HERE, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    tail = (r.stdout or r.stderr).strip().splitlines()[-1:] or [""]
    log(f"{script} {' '.join(args)} -> exit {r.returncode}: {tail[0][:200]}")
    return r.returncode


def ids(kind: str) -> set[str]:
    f = HERE / f"list_{kind}.txt"
    return {r.split("|", 1)[0] for r in f.read_text(encoding="utf-8").splitlines() if r.strip()} if f.exists() else set()


def have(folder: str, kind: str, ext: str) -> set[str]:
    return {p.stem.split("_", 1)[1] for p in (HERE / folder).glob(f"{kind}_*{ext}")}


def main() -> int:
    if (HERE / "ALL_DONE").exists():
        return 0
    notes_before = len(list((HERE / "notes").glob("*.md")))
    run("fetch_transcripts.py", "--daily")
    # Streams (~196 h, ~$30 to extract) are held until the owner adds API credits
    # (2026-09-24: $28.94 left, needed for the trading desk). Create research/STREAMS_OK
    # to include them. Transcripts still download; only the paid extraction waits.
    kinds = "videos,external,shorts" + (",streams" if (HERE / "STREAMS_OK").exists() else "")
    run("extract_knowledge.py", "--kinds", kinds, "--workers", "4")
    notes_after = len(list((HERE / "notes").glob("*.md")))

    teaching = ids("videos") | ids("external")
    teaching_done = all(v in have("notes", k, ".md")
                        for k in ("videos", "external") for v in ids(k))
    kb = HERE / "creamer_knowledge.md"
    newest_note = max((p.stat().st_mtime for p in (HERE / "notes").glob("*.md")), default=0)
    # Rebuild (~$2.40 each) only when it is worth it: first build, 25+ new notes since the
    # last build, or everything downloaded. Nightly trickles of a few shorts no longer
    # trigger a full rebuild (decided 2026-09-27 under the owner's delegation).
    new_since = sum(1 for p in (HERE / "notes").glob("*.md")
                    if not kb.exists() or p.stat().st_mtime > kb.stat().st_mtime)
    everything_noted = all(v in have("notes", k, ".md")
                           for k in ("videos", "external", "shorts", "streams") for v in ids(k))
    if teaching_done and (not kb.exists() or new_since >= 25 or (everything_noted and new_since)):
        run("synthesize.py")
    elif new_since:
        log(f"rebuild deferred: {new_since} new notes since last build (threshold 25)")
    everything = all(v in have("notes", k, ".md")
                     for k in ("videos", "external", "shorts", "streams") for v in ids(k))
    if everything and kb.exists() and kb.stat().st_mtime >= newest_note:
        (HERE / "ALL_DONE").write_text(f"{datetime.now():%Y-%m-%d %H:%M}\n", encoding="utf-8")
        log("ALL DONE: every video, short and stream has notes; knowledge base rebuilt.")
    log(f"notes {notes_before} -> {notes_after}; teaching videos complete: {teaching_done} "
        f"({len(teaching)} total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
