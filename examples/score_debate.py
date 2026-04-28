"""Rule-based persona-drift scorer for steelman debate runs.

Reads every workspace/debate/turn_*.md file in each run dir provided,
scores each turn on persona adherence, prints a side-by-side table,
and summarizes. Deterministic — no LLM calls.

Rubric:
  + rude_hits      : sum of mocking markers (dismissal phrases,
                     scare-quote pairs, ALL-CAPS words, '!' marks,
                     short mocking questions). Capped at 5.
  - hedge_hits     : count of hedging/conceding phrases. Each costs 2.
  - brief_hits     : count of policy-brief connectors (furthermore,
                     moreover, in conclusion, ...). Each costs 1.
  + length_ok      : +1 if ≤120 words, -2 if over.
  + first_is_jab   : +1 if first sentence is short or contains a
                     mocking marker or ends with "?".

Composite = rude + length_ok + first_is_jab - hedge_penalty - brief_penalty.
Higher = more in-persona.

Usage:
  python examples/score_debate.py runs/ai-regulation-debate-full runs/ai-regulation-debate-inlined-history
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


RUDE_PHRASES = [
    "cope", "lol", "read a book", "buddy", "clown", "mate",
    "yikes", "pfft", "oh please", "sure, buddy", "sure buddy",
    "what a joke", "come on", "be serious", "grow up",
    "death cult", "fantasy", "delusional", "nonsense", "handwave",
    "lmao", "bruh", "dude,", "please.",
]

HEDGE_PHRASES = [
    "fair point", "valid point", "i see your point", "you're right",
    "i agree", "you have a point", "reasonable point", "nuanced",
    "it's important to note", "to be fair", "that said",
    "however, ", "on the other hand", "admittedly", "granted,",
    "in fairness",
]

BRIEF_PHRASES = [
    "furthermore", "moreover", "in summary", "to conclude",
    "in conclusion", "firstly", "secondly", "thirdly",
    "first,", "second,", "third,", "finally,",
    "additionally,", "importantly,",
]


def _extract_body(text: str) -> str:
    """Strip the '# Turn NN — SIDE' header line if present."""
    lines = text.splitlines()
    while lines and (not lines[0].strip() or lines[0].lstrip().startswith("#")):
        lines.pop(0)
    return "\n".join(lines).strip()


def _count_phrases(text_lower: str, phrases: list[str]) -> int:
    return sum(text_lower.count(p) for p in phrases)


def _count_short_mocking_questions(body: str) -> int:
    sentences = re.split(r"(?<=[.!?])\s+", body)
    n = 0
    for s in sentences:
        if "?" in s:
            words = s.split()
            if 1 <= len(words) <= 12:
                n += 1
    return n


def _count_all_caps_words(body: str) -> int:
    words = re.findall(r"[A-Za-z]+", body)
    return sum(1 for w in words if len(w) >= 3 and w.isupper())


def _count_scare_quote_pairs(body: str) -> int:
    return body.count('"') // 2


def score_turn(text: str) -> dict:
    body = _extract_body(text)
    body_lower = body.lower()
    words = body.split()
    word_count = len(words)

    scare_quotes = _count_scare_quote_pairs(body)
    all_caps = _count_all_caps_words(body)
    exclam = body.count("!")
    mocking_qs = _count_short_mocking_questions(body)
    rude_markers = _count_phrases(body_lower, RUDE_PHRASES)

    rude_hits_raw = rude_markers + scare_quotes + all_caps + exclam + mocking_qs
    rude_hits_capped = min(5, rude_hits_raw)

    hedge_hits = _count_phrases(body_lower, HEDGE_PHRASES)
    brief_hits = _count_phrases(body_lower, BRIEF_PHRASES)

    length_ok = word_count <= 120
    length_bonus = 1 if length_ok else -2

    first_sentence = re.split(r"(?<=[.!?])\s+", body, maxsplit=1)[0] if body else ""
    first_words = first_sentence.split()
    first_short = 1 <= len(first_words) <= 10
    first_has_marker = any(p in first_sentence.lower() for p in RUDE_PHRASES)
    first_ends_q = first_sentence.strip().endswith("?")
    first_is_jab = 1 if (first_short or first_has_marker or first_ends_q) else 0

    hedge_penalty = hedge_hits * 2
    brief_penalty = brief_hits * 1

    composite = rude_hits_capped + length_bonus + first_is_jab - hedge_penalty - brief_penalty

    return {
        "words": word_count,
        "rude": rude_hits_raw,
        "scare_q": scare_quotes,
        "caps": all_caps,
        "excl": exclam,
        "mock_q": mocking_qs,
        "hedge": hedge_hits,
        "brief": brief_hits,
        "len_ok": length_ok,
        "jab1": first_is_jab,
        "composite": composite,
    }


def score_run(run_dir: Path) -> list[tuple[str, dict]]:
    debate_dir = run_dir / "workspace" / "debate"
    if not debate_dir.exists():
        return []
    turns = sorted(debate_dir.glob("turn_*.md"))
    scored = []
    for p in turns:
        text = p.read_text(encoding="utf-8")
        scored.append((p.name, score_turn(text)))
    return scored


def print_run_table(label: str, scored: list[tuple[str, dict]]) -> None:
    print(f"\n{label}")
    print("-" * len(label))
    header = f"{'turn':<22} {'words':>5} {'rude':>4} {'scq':>3} {'caps':>4} {'excl':>4} {'mqs':>3} {'hedge':>5} {'brief':>5} {'len_ok':>6} {'jab1':>4} {'SCORE':>5}"
    print(header)
    print("-" * len(header))
    total = 0
    for name, s in scored:
        print(
            f"{name:<22} {s['words']:>5} {s['rude']:>4} {s['scare_q']:>3} "
            f"{s['caps']:>4} {s['excl']:>4} {s['mock_q']:>3} "
            f"{s['hedge']:>5} {s['brief']:>5} "
            f"{str(s['len_ok']):>6} {s['jab1']:>4} {s['composite']:>5}"
        )
        total += s["composite"]
    n = max(1, len(scored))
    avg = total / n
    print("-" * len(header))
    print(f"{'TOTAL':<22} {'':>5} {'':>4} {'':>3} {'':>4} {'':>4} {'':>3} {'':>5} {'':>5} {'':>6} {'':>4} {total:>5}")
    print(f"{'AVG per turn':<22} {'':>5} {'':>4} {'':>3} {'':>4} {'':>4} {'':>3} {'':>5} {'':>5} {'':>6} {'':>4} {avg:>5.2f}")


def print_comparison(runs: list[tuple[str, list[tuple[str, dict]]]]) -> None:
    if len(runs) < 2:
        return
    print("\n\nPer-turn composite-score comparison")
    print("-" * 60)
    header = f"{'turn':<22}"
    for label, _ in runs:
        header += f" {label[:14]:>15}"
    print(header)
    print("-" * len(header))
    max_len = max(len(s) for _, s in runs)
    for i in range(max_len):
        turn_name = ""
        row = ""
        for label, scored in runs:
            if i < len(scored):
                if not turn_name:
                    turn_name = scored[i][0]
                row += f" {scored[i][1]['composite']:>15}"
            else:
                row += f" {'--':>15}"
        print(f"{turn_name:<22}{row}")
    print("-" * len(header))
    total_row = f"{'TOTAL':<22}"
    avg_row = f"{'AVG':<22}"
    for _, scored in runs:
        total = sum(s["composite"] for _, s in scored)
        avg = total / max(1, len(scored))
        total_row += f" {total:>15}"
        avg_row += f" {avg:>15.2f}"
    print(total_row)
    print(avg_row)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python examples/score_debate.py <run_dir> [<run_dir> ...]")
        return 1
    runs = []
    for arg in sys.argv[1:]:
        run_dir = Path(arg).resolve()
        if not run_dir.exists():
            print(f"ERROR: {run_dir} does not exist")
            return 1
        scored = score_run(run_dir)
        label = run_dir.name
        print_run_table(f"=== {label} ===", scored)
        runs.append((label, scored))
    print_comparison(runs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
