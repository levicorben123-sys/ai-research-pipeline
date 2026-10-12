# AI Research Pipeline — turning hours of video into a testable spec

An automated pipeline that uses an LLM (Anthropic Claude) to turn a large library of trading-education
videos into structured notes, a merged knowledge base, and finally a precise, testable strategy spec
for a futures trading bot (MNQ, paper-only research).

Built with [Claude Code](https://claude.com/claude-code) as the coding agent; I directed the project and
made the decisions.

**Status (Oct 2026): shelved Oct 7** before the strategy spec reached a backtest. Kept here as a working example of the LLM pipeline, not as a trading result.

## Pipeline
1. **Fetch** — `research/fetch_transcripts.py` downloads transcripts for a channel's videos
   (resumable, stops cleanly if rate-limited).
2. **Extract** — `research/extract_knowledge.py` sends each transcript to Claude with a fixed schema and
   saves one structured note per video (rules, definitions, examples, open questions).
3. **Synthesize** — `research/synthesize.py` merges all notes into one knowledge base and a numbered
   rulebook, flagging contradictions.
4. **Automate** — `research/research_daily.py` runs all three steps nightly as a hidden scheduled job
   until the library is done.

Result so far: 65 notes (48 full videos, an interview and 15 shorts) merged into one knowledge base,
used to answer the open questions in [`strategy_spec.md`](strategy_spec.md).

## Design choices
- Discretionary judgment calls in the source material are turned into measurable rules and explicitly
  marked as approximations.
- Nothing trades until the spec is backtested with realistic costs on data not used to design it.
- Source transcripts and notes are **not** included in this repo — they are the original creator's content.
