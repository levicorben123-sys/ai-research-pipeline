"""Merge all per-video notes into one knowledge base: research/creamer_knowledge.md.

Reads every research/notes/*.md, asks a strong model to consolidate them into a
single rulebook organised by topic, with evidence (video links), consensus vs
contradictions, what he says vs what he does, and answers to the open questions
in ../strategy_spec.md. Re-run whenever more notes arrive; it rebuilds from scratch.

Usage:
    python synthesize.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
load_dotenv(Path.home() / "trading-desk" / ".env")

import anthropic  # noqa: E402

MODEL = "claude-opus-5"
PRICE_IN, PRICE_OUT = 5.00, 25.00
OUT = HERE / "creamer_knowledge.md"

SYSTEM = """You consolidate research notes about Chris Creamer's MNQ/NQ futures order-flow trading
method into a single rulebook that engineers will turn into a trading bot. Precision and honesty
matter more than polish:
- Merge duplicates; keep every distinct rule, number, definition and condition.
- Cite evidence for each item as the video title in brackets, e.g. [How I Map My Trades...].
- Mark each rule's support: (consistent across N videos) or (mentioned once).
- Flag contradictions explicitly, and where what he SAYS differs from what he DOES live.
- Separate firm rules from discretionary judgment; for discretionary items, propose a
  measurable bot rule and label it PROPOSED APPROXIMATION.
- Never invent. If something is unknown, say "not stated in the material so far"."""

TASK = """Write the knowledge base in markdown with these sections:

# Chris Creamer method - knowledge base (as of {today}, from {n} videos)
## 1. The framework in one page (his sequence, end to end)
## 2. Context: bias, market structure, auction state, sessions (Asia/London/NY)
## 3. Gamma / GEX (source, definitions, levels, how it changes trade selection)
## 4. Location: value area, POC, premium/discount, fib levels, confluence
## 5. Order-flow definitions (delta, absorption, imbalances, stacked imbalances, exhaustion, dominance shift, failed auction...)
## 6. Entry models (each model: preconditions, exact trigger sequence, timeframe, chart type)
## 7. Stops
## 8. Targets and trade management
## 9. Filters and no-trade conditions
## 10. Risk, sizing, daily limits, prop-firm account structure
## 11. Tools and settings (platforms, footprint settings, numbers)
## 12. His results and track record (as he reports them, incl. losing periods)
## 13. Mistakes and lessons he repeats
## 14. Says vs does, and contradictions
## 15. Answers to the open spec questions
  - G1 GEX source/definition; Q2 20,000-contract filter NQ or MNQ; Q3 absorption/dominance
    shift definition; Q4 max trades, daily loss stop, sizing; Q5 shorts symmetric?
  For each: answer, evidence, confidence, and what is still unknown.
## 16. Bot rulebook draft (numbered, testable rules; mark every PROPOSED APPROXIMATION)
## 17. Gaps: what the material does not tell us and how we could find out

NOTES FROM {n} VIDEOS:
"""


DIGESTS = HERE / "digests"
DIGEST_MODEL = "claude-sonnet-5"
BATCH = 20
DIGEST_SYSTEM = """You condense per-video research notes about Chris Creamer's MNQ/NQ order-flow method
into one digest for a later rulebook merge. Keep every distinct rule, number, definition,
condition, live-trade example, mistake and statistic, each with its short quote and the video
title in brackets. Drop repetition and filler. Mark anything that contradicts or refines the
standard framework (context -> gamma -> location -> order-flow confirmation -> stop/target).
Never invent."""


def digest(client, kind: str, idx: int, batch: list[Path]) -> str:
    """Condensed notes for one batch of shorts/streams, cached by content hash."""
    import hashlib
    texts = [p.read_text(encoding="utf-8") for p in batch]
    h = hashlib.sha256("\n".join(texts).encode()).hexdigest()[:12]
    out = DIGESTS / f"{kind}_{idx:02d}_{h}.md"
    if out.exists():
        return out.read_text(encoding="utf-8")
    for old in DIGESTS.glob(f"{kind}_{idx:02d}_*.md"):
        old.unlink()
    with client.messages.stream(model=DIGEST_MODEL, max_tokens=32000, system=DIGEST_SYSTEM,
                                messages=[{"role": "user", "content":
                                           f"Digest these {len(batch)} {kind} notes:\n\n"
                                           + "\n\n=====\n\n".join(texts)}]) as s:
        msg = s.get_final_message()
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    out.write_text(f"# Digest: {kind} batch {idx} ({len(batch)} videos)\n\n{text}\n", encoding="utf-8")
    print(f"digest {out.name}: in={msg.usage.input_tokens} out={msg.usage.output_tokens}")
    return out.read_text(encoding="utf-8")


def main() -> int:
    # Staged merge (2026-09-27): teaching videos, the interview and the web research go in
    # whole; shorts and streams (~150 long stream notes would overflow one context window)
    # are condensed in batches of 20 first, and each batch digest is cached so later runs
    # only redo batches whose notes changed.
    DIGESTS.mkdir(exist_ok=True)
    notes = sorted((HERE / "notes").glob("*.md"))
    core = [p for p in notes if p.stem.split("_", 1)[0] in ("videos", "external")]
    client = anthropic.Anthropic(max_retries=6)
    parts = [p.read_text(encoding="utf-8") for p in core]
    for kind in ("shorts", "streams"):
        rest = [p for p in notes if p.stem.startswith(kind + "_")]
        for i in range(0, len(rest), BATCH):
            parts.append(digest(client, kind, i // BATCH, rest[i:i + BATCH]))
    corpus = "\n\n=====\n\n".join(parts)
    prompt = TASK.format(today=date.today().isoformat(), n=len(notes)) + corpus
    # Streamed: this network drops HTTP connections silent for ~60s.
    with client.messages.stream(model=MODEL, max_tokens=64000, system=SYSTEM,
                                output_config={"effort": "high"},
                                messages=[{"role": "user", "content": prompt}]) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        print("refused; nothing written")
        return 1
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    OUT.write_text(text + "\n", encoding="utf-8")
    cost = msg.usage.input_tokens / 1e6 * PRICE_IN + msg.usage.output_tokens / 1e6 * PRICE_OUT
    print(f"wrote {OUT} from {len(notes)} notes | in={msg.usage.input_tokens} "
          f"out={msg.usage.output_tokens} stop={msg.stop_reason} ~${cost:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
