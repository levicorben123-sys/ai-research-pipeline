"""Extract every piece of trading knowledge from each Creamer transcript.

For each research/transcripts/*.txt without notes yet, asks Claude for structured
notes (rules, numbers, definitions, filters, gamma usage, risk, mistakes, ...),
each item with a short verbatim quote, and writes research/notes/<same name>.md.
Resumable; runs a few transcripts in parallel; prints running cost.

Usage:
    python extract_knowledge.py [--kinds videos,shorts,streams] [--workers 4]
"""

from __future__ import annotations

import argparse
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
load_dotenv(Path.home() / "trading-desk" / ".env")   # ANTHROPIC_API_KEY lives there

import anthropic  # noqa: E402

MODEL = "claude-sonnet-5"      # bulk extraction; synthesis uses a stronger model
PRICE_IN, PRICE_OUT = 2.00, 10.00
NOTES = HERE / "notes"
NOTES.mkdir(exist_ok=True)

SYSTEM = """You extract trading knowledge from transcripts of Chris Creamer, an MNQ/NQ futures
order-flow day trader (Robbins World Cup Micro Day Trading Championship winner). The goal is to
rebuild his method as precise, testable rules for a trading bot, so completeness and precision
matter more than brevity. Transcripts are auto-generated captions: fix obvious caption errors
(e.g. "delta" misheard) only when certain.

Rules:
- Capture EVERYTHING rule-like: definitions, numeric thresholds, settings, conditions, filters,
  sequences, exceptions, "I only take X when Y", "I never...", time windows, sizes, targets.
- Every item gets a short verbatim quote (<= 25 words) from the transcript as evidence.
- Separate what he SAYS his rule is from what he DOES in live examples when they differ.
- Record losses, mistakes and rule-breaking with the cause he gives.
- Do not invent anything. If the transcript has nothing for a section, write "none".
- Numbers: always say whether they refer to NQ, MNQ, ES, or unspecified."""

FORMAT = """Write markdown with exactly these sections (bullet points, each with a quote):

## Summary (2-3 sentences: what this video is and how rule-relevant it is, 1-5)
## Context / environment (market regime, gamma/GEX, news, day type)
## Gamma / GEX (source, definitions, levels, how it changes trade selection)
## Location (premium/discount, value area, POC, fib levels, key levels, pre-market mapping)
## Order-flow definitions (delta, absorption, imbalances, stacked imbalances, exhaustion, dominance shift, etc.)
## Entry models and triggers (exact sequences, timeframes, chart types)
## Stops
## Targets and trade management (partials, trailing, breakeven)
## Filters / no-trade conditions (volume/participation, time, news, chop)
## Risk, sizing and prop-firm rules (per-trade risk, daily limits, max trades, account structure)
## Tools and settings (platform, footprint settings, indicators, numbers)
## Live trade examples (what happened, why he took it, outcome)
## Mistakes, losses and lessons (with the cause he gives)
## Longs vs shorts (symmetric or not)
## Statistics he reports (win rate, R, PnL, streaks, drawdowns)
## Anything else rule-relevant"""

_lock = threading.Lock()
_cost = [0.0]


def extract(client: anthropic.Anthropic, path: Path) -> str:
    out = NOTES / (path.stem + ".md")
    if out.exists():
        return f"skip {path.stem}"
    text = path.read_text(encoding="utf-8")
    header = "\n".join(text.splitlines()[:3])
    # Streamed: this network drops HTTP connections silent for ~60s.
    with client.messages.stream(
        model=MODEL, max_tokens=16000, system=SYSTEM,
        messages=[{"role": "user", "content": f"{FORMAT}\n\nTRANSCRIPT:\n{text}"}],
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        return f"REFUSED {path.stem}"
    body = "".join(b.text for b in msg.content if b.type == "text").strip()
    out.write_text(f"{header}\n\n{body}\n", encoding="utf-8")
    c = msg.usage.input_tokens / 1e6 * PRICE_IN + msg.usage.output_tokens / 1e6 * PRICE_OUT
    with _lock:
        _cost[0] += c
        total = _cost[0]
    return (f"ok   {path.stem} in={msg.usage.input_tokens} out={msg.usage.output_tokens} "
            f"${c:.3f} (running ${total:.2f})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kinds", default="videos,external,shorts,streams")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    kinds = args.kinds.split(",")
    # Paid stream extraction (~$30) waits for the owner's go-ahead (2026-09-24, low API
    # credits needed by the trading desk): create research/STREAMS_OK to allow it.
    if "streams" in kinds and not (HERE / "STREAMS_OK").exists():
        kinds.remove("streams")
        print("streams held: create research/STREAMS_OK to extract them")
    files = sorted(p for p in (HERE / "transcripts").glob("*.txt")
                   if p.stem.split("_", 1)[0] in kinds)
    client = anthropic.Anthropic(max_retries=6)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(extract, client, p): p for p in files}
        for f in as_completed(futs):
            try:
                print(f.result(), flush=True)
            except Exception as e:
                print(f"FAIL {futs[f].stem}: {type(e).__name__}: {str(e)[:150]}", flush=True)
    print(f"done; total cost this run ${_cost[0]:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
