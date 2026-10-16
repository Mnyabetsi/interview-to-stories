"""Run the generator on every sample transcript and report quality metrics.

Usage:
    python eval.py                       # generate backlogs for all samples, then evaluate
    python eval.py --use-saved           # evaluate the backlogs saved by an earlier run (cheaper)
    python eval.py --model claude-sonnet-5-5 --effort low

Needs ANTHROPIC_API_KEY. Backlogs are saved to samples/outputs/ (the app's "See an example"
mode shows them) and the results are summarised in eval_results.md.

Two kinds of checks run on every backlog:
- Rule-based quality checks (quality.py): INVEST heuristics and verbatim quote grounding.
- Coverage (coverage.py), for samples with an answer key in samples/expected/: how many of the
  requirements a human PO expected were captured.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from coverage import check_coverage, load_expected
from generator import DEFAULT_MODEL, MODELS, GenerationError, generate_backlog
from quality import check_backlog

ROOT = Path(__file__).parent
SAMPLES_DIR = ROOT / "samples"
OUTPUTS_DIR = SAMPLES_DIR / "outputs"
EXPECTED_DIR = SAMPLES_DIR / "expected"


def load_or_generate(path: Path, transcript: str, args) -> tuple[dict, dict]:
    saved = OUTPUTS_DIR / f"{path.stem}.json"
    if args.use_saved:
        data = json.loads(saved.read_text(encoding="utf-8"))
        return data["backlog"], data.get("meta", {})
    result = generate_backlog(transcript, model=args.model, effort=args.effort, language=args.language)
    meta = {"model": result.model, "effort": args.effort, "seconds": result.seconds,
            "cost": result.cost_usd, "tokens": result.input_tokens + result.output_tokens,
            "fell_back": result.fell_back}
    saved.write_text(json.dumps({"backlog": result.data, "meta": meta}, indent=2, ensure_ascii=False),
                     encoding="utf-8")
    return result.data, meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=list(MODELS))
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--language", default="English")
    parser.add_argument("--use-saved", action="store_true", help="Reuse backlogs in samples/outputs/ instead of generating.")
    args = parser.parse_args()

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    rows, coverage_details, eval_cost = [], [], 0.0
    for path in sorted(SAMPLES_DIR.glob("*.txt")):
        transcript = path.read_text(encoding="utf-8")
        print(f"→ {path.name} …", flush=True)
        try:
            backlog, meta = load_or_generate(path, transcript, args)
        except FileNotFoundError:
            print("   skipped: no saved backlog (run without --use-saved first)")
            continue
        except GenerationError as e:
            print(f"   failed: {e}")
            continue

        report = check_backlog(backlog, transcript)
        row = {
            "sample": path.stem, "stories": report.story_count, "score": report.average_score,
            "quotes": sum(report.quote_counts.values()), "grounded": report.grounding_rate,
            "ac": report.ac_coverage, "questions": len(backlog.get("open_questions", [])),
            "seconds": meta.get("seconds", 0), "cost": meta.get("cost", 0), "found": None,
        }

        expected_file = EXPECTED_DIR / f"{path.stem}.md"
        if expected_file.exists():
            try:
                cov = check_coverage(backlog, load_expected(expected_file))
            except GenerationError as e:
                print(f"   coverage check failed: {e}")
            else:
                eval_cost += cov.judge.cost_usd
                row.update(found=cov.found_rate, found_partial=cov.found_or_partial_rate,
                           expected=len(cov.verdicts), covered=cov.counts["covered"])
                (OUTPUTS_DIR / f"{path.stem}.coverage.json").write_text(json.dumps(
                    [{"id": v.item.id, "kind": v.item.kind, "expected": v.item.text, "verdict": v.verdict,
                      "evidence": v.evidence, "explanation": v.explanation} for v in cov.verdicts],
                    indent=2, ensure_ascii=False), encoding="utf-8")
                coverage_details.append((path.stem, [v for v in cov.verdicts if v.verdict != "covered"]))

        rows.append(row)
        found = f" · found {row['covered']}/{row['expected']} expected" if row["found"] is not None else ""
        print(f"   {row['stories']} stories · score {row['score']} · grounded {row['grounded']:.0%}{found}")

    if not rows:
        return
    n = len(rows)
    with_cov = [r for r in rows if r["found"] is not None]
    pct = lambda r, k: f"{r[k]:.0%}" if r.get(k) is not None else "–"
    lines = [
        f"# Evaluation results ({date.today().isoformat()})",
        "",
        f"Model `{meta.get('model', args.model)}`, effort `{meta.get('effort', args.effort)}`, output language {args.language}.",
        "",
        "| Sample | Stories | Avg. quality | Quotes verified | Expected reqs found | Found incl. partial | Stories with ≥2 AC | Open questions | Time | Cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines += [f"| {r['sample']} | {r['stories']} | {r['score']:.0f} | {r['grounded']:.0%} of {r['quotes']} | "
              f"{pct(r, 'found')} | {pct(r, 'found_partial')} | {r['ac']:.0%} | {r['questions']} | "
              f"{r['seconds']:.0f}s | ${r['cost']:.2f} |" for r in rows]
    total_expected = sum(r["expected"] for r in with_cov)
    lines.append(
        f"| **Total / average** | {sum(r['stories'] for r in rows)} | {sum(r['score'] for r in rows) / n:.0f} | "
        f"{sum(r['grounded'] * r['quotes'] for r in rows) / max(1, sum(r['quotes'] for r in rows)):.0%} of "
        f"{sum(r['quotes'] for r in rows)} | "
        + (f"{sum(r['covered'] for r in with_cov)}/{total_expected} "
           f"({sum(r['covered'] for r in with_cov) / total_expected:.0%}) | "
           f"{sum(r['found_partial'] * r['expected'] for r in with_cov) / total_expected:.0%} | "
           if with_cov else "– | – | ")
        + f"{sum(r['ac'] for r in rows) / n:.0%} | {sum(r['questions'] for r in rows) / n:.1f} | "
          f"{sum(r['seconds'] for r in rows) / n:.0f}s | ${sum(r['cost'] for r in rows) / n:.2f} |")

    if coverage_details:
        lines += ["", "## Expected items not fully found", "",
                  "Review these by hand. The reviewer can be wrong in both directions.", ""]
        for sample, misses in coverage_details:
            lines.append(f"**{sample}**" + ("" if misses else ": all expected items found."))
            lines += [f"- `{v.item.id}` {v.verdict.upper()}: {v.item.text}  \n  _{v.explanation}_" for v in misses]
            lines.append("")
    lines += ["", f"Coverage review cost: ${eval_cost:.2f}. Full verdicts: `samples/outputs/*.coverage.json`."]

    (ROOT / "eval_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines))


if __name__ == "__main__":
    main()
