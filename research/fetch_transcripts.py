"""Download transcripts for every video in research/list_{videos,shorts,streams}.txt.

Skips transcripts already on disk, paces requests so YouTube does not rate-limit
the IP, and logs every success/failure to research/fetch_log.txt. Safe to re-run:
it resumes where it stopped.
"""

import random
import sys
import time
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi

HERE = Path(__file__).resolve().parent
OUT = HERE / "transcripts"
LOG = HERE / "fetch_log.txt"
OUT.mkdir(exist_ok=True)


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> int:
    # --daily: one knock per day. If YouTube still blocks this IP, stop at once instead of
    # waiting and retrying (repeated retries likely kept the 2026-09-23 block alive).
    daily = "--daily" in sys.argv
    api = YouTubeTranscriptApi()
    order = ["videos", "external", "shorts", "streams"]
    blocked = 0
    for kind in order:
        rows = [r.split("|", 2) for r in (HERE / f"list_{kind}.txt").read_text(
            encoding="utf-8").splitlines() if r.strip()]
        log(f"== {kind}: {len(rows)} items")
        for vid, dur, title in rows:
            path = OUT / f"{kind}_{vid}.txt"
            if path.exists():
                continue
            try:
                t = api.fetch(vid)
                text = " ".join(s.text.replace("\n", " ") for s in t)
                path.write_text(f"# {title}\n# kind: {kind} | duration_s: {dur}\n"
                                f"# https://www.youtube.com/watch?v={vid}\n\n{text}\n",
                                encoding="utf-8")
                log(f"ok   {kind} {vid} {len(text.split()):>6} words  {title[:70]}")
                blocked = 0
            except Exception as e:
                name = type(e).__name__
                log(f"FAIL {kind} {vid} {name}: {str(e).splitlines()[0][:100]}  {title[:60]}")
                if "Block" in name or "TooMany" in name or "429" in str(e):
                    if daily:
                        log("blocked (daily mode) - stopping until tomorrow's run")
                        return 2
                    blocked += 1
                    wait = min(600, 60 * blocked)
                    log(f"rate-limited; waiting {wait}s")
                    time.sleep(wait)
                    if blocked >= 5:
                        log("still blocked after 5 waits; stopping - re-run later to resume")
                        return 1
            # Slow pace: at 2-5 s YouTube IP-blocked us after ~30 videos (2026-09-23).
            time.sleep(random.uniform(15.0, 30.0))
    log("== done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
