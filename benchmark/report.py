"""Aggregates benchmark/results/{multi_agent,baseline_single_shot}.json
into a markdown comparison table and a bar chart, for the writeup/video.

Usage: python3 benchmark/report.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "benchmark" / "results"


def _load(name: str) -> list[dict]:
    path = RESULTS_DIR / name
    if not path.exists():
        return []
    return json.loads(path.read_text())


def build_markdown(multi: list[dict], baseline: list[dict]) -> str:
    baseline_by_id = {r["issue_id"]: r for r in baseline}
    lines = [
        "| Issue | Category | Multi-agent | Baseline (single-shot) |",
        "|---|---|---|---|",
    ]
    for r in multi:
        b = baseline_by_id.get(r["issue_id"])
        b_mark = "✅" if b and b["resolved"] else "❌" if b else "n/a"
        m_mark = "✅" if r["resolved"] else "❌"
        lines.append(
            f"| {r['issue_id']} | {r['category']} | {m_mark} ({r['attempts']} attempt(s)) | {b_mark} |"
        )

    m_rate = sum(1 for r in multi if r["resolved"])
    b_rate = sum(1 for r in baseline if r["resolved"])
    lines.append("")
    lines.append(
        f"**Multi-agent pipeline: {m_rate}/{len(multi)} resolved. "
        f"Single-shot baseline: {b_rate}/{len(baseline)} resolved.**"
    )
    return "\n".join(lines)


def build_chart(multi: list[dict], baseline: list[dict], out_path: Path) -> None:
    categories = sorted({r["category"] for r in multi})
    multi_by_cat = {c: 0 for c in categories}
    baseline_by_cat = {c: 0 for c in categories}
    totals = {c: 0 for c in categories}

    baseline_by_id = {r["issue_id"]: r for r in baseline}
    for r in multi:
        c = r["category"]
        totals[c] += 1
        if r["resolved"]:
            multi_by_cat[c] += 1
        b = baseline_by_id.get(r["issue_id"])
        if b and b["resolved"]:
            baseline_by_cat[c] += 1

    x = range(len(categories))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(
        [i - width / 2 for i in x],
        [multi_by_cat[c] for c in categories],
        width,
        label="Multi-agent",
    )
    ax.bar(
        [i + width / 2 for i in x],
        [baseline_by_cat[c] for c in categories],
        width,
        label="Single-shot baseline",
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(categories, rotation=20)
    ax.set_ylabel("Issues resolved")
    ax.set_title("Multi-agent pipeline vs. single-shot baseline")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Chart -> {out_path}")


def main() -> None:
    multi = _load("multi_agent.json")
    baseline = _load("baseline_single_shot.json")
    if not multi:
        print("No multi_agent.json results found -- run run_benchmark.py first.")
        return

    markdown = build_markdown(multi, baseline)
    report_path = RESULTS_DIR / "report.md"
    report_path.write_text(markdown)
    print(markdown)
    print(f"\nMarkdown report -> {report_path}")

    if baseline:
        build_chart(multi, baseline, RESULTS_DIR / "comparison_chart.png")
    else:
        print("No baseline_single_shot.json results found -- skipping chart.")


if __name__ == "__main__":
    main()
