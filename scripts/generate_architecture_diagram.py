"""Generates docs/architecture.png -- a simple boxes-and-arrows diagram of
the pipeline, for the README/writeup/video. No external binaries needed
(pure matplotlib), since this dev environment has no `dot`/Graphviz binary.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "docs" / "architecture.png"


def box(ax, xy, w, h, text, color="#4C78A8", fontsize=9):
    rect = mpatches.FancyBboxPatch(
        xy,
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.06",
        linewidth=1.2,
        edgecolor="#222222",
        facecolor=color,
    )
    ax.add_patch(rect)
    ax.text(
        xy[0] + w / 2,
        xy[1] + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color="white",
        wrap=True,
    )


def arrow(ax, start, end, style="-|>"):
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(arrowstyle=style, color="#333333", lw=1.4),
    )


def main() -> None:
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7)
    ax.axis("off")

    # Entrypoints
    box(ax, (0.3, 5.9), 2.2, 0.7, "benchmark/\nrun_benchmark.py", "#54A24B")
    box(ax, (0.3, 4.9), 2.2, 0.7, "agent/cli.py\n(demo mode)", "#54A24B")

    # Triage
    box(ax, (3.1, 5.4), 1.9, 0.9, "TriageAgent\n(LLM)", "#4C78A8")

    # Retry loop group
    loop_rect = mpatches.FancyBboxPatch(
        (5.5, 3.6), 3.2, 2.9, boxstyle="round,pad=0.05", linewidth=1.4,
        edgecolor="#B23A48", facecolor="none", linestyle="--",
    )
    ax.add_patch(loop_rect)
    ax.text(7.1, 6.6, "retry up to 3x", ha="center", fontsize=9, color="#B23A48")

    box(ax, (5.8, 5.3), 2.6, 0.8, "CodingAgent (LLM)\n+ read_repo_file tool", "#4C78A8")
    box(ax, (5.8, 4.3), 2.6, 0.8, "test_runner_node\n(deterministic, sandboxed)", "#E45756")
    box(ax, (5.8, 3.3), 2.6, 0.8, "ReviewAgent (LLM)\nAPPROVED / REJECTED", "#4C78A8")

    arrow(ax, (7.1, 5.3), (7.1, 5.1))
    arrow(ax, (7.1, 4.3), (7.1, 4.1))
    arrow(ax, (5.8, 3.7), (5.8, 5.1))  # feedback loop back to coding

    # PR agent + human gate
    box(ax, (9.1, 4.6), 1.7, 0.8, "PRAgent (LLM)\ndrafts only", "#4C78A8")
    box(ax, (9.1, 3.3), 1.7, 0.9, "Human\napproval gate", "#F58518")
    box(ax, (9.1, 2.1), 1.7, 0.8, "GitHub MCP\ncreate_pull_request", "#72B7B2")

    arrow(ax, (2.5, 6.25), (3.1, 5.85))
    arrow(ax, (2.5, 5.25), (3.1, 5.7))
    arrow(ax, (5.0, 5.85), (5.8, 5.7))
    arrow(ax, (8.4, 5.3), (9.1, 5.0))
    arrow(ax, (9.95, 4.6), (9.95, 4.2))
    arrow(ax, (9.95, 3.3), (9.95, 2.9))

    # Security footnotes
    box(ax, (0.3, 0.3), 4.4, 1.4,
        "Security: fine-grained PAT (single repo) - scrubbed subprocess env\n"
        "- CPU/memory/timeout limits - ephemeral temp dir per attempt\n"
        "- slopsquatting guard (rejects new/unapproved deps)\n"
        "- human approval gate before any real PR",
        "#5B5B5B", fontsize=8)

    box(ax, (5.3, 0.3), 5.5, 1.4,
        "Agent Skills (.agents/skills/*/SKILL.md, open standard, Antigravity-compatible)\n"
        "OpenTelemetry trajectory export (agent/tracing.py)\n"
        "Spec-driven tests: Gherkin .feature -> pytest-bdd (missing-tests issues)\n"
        "Dockerfile + Cloud Run deploy script",
        "#5B5B5B", fontsize=8)

    ax.set_title(
        "Benchmarked GitHub Issue-Solving Agent -- Pipeline Architecture",
        fontsize=13,
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(OUT_PATH, dpi=160)
    print(f"Diagram -> {OUT_PATH}")


if __name__ == "__main__":
    main()
