---
name: run-benchmark
description: Run the full 10-issue benchmark (multi-agent pipeline and single-shot baseline) and generate the comparison report/chart. Use when asked to benchmark, evaluate, or re-generate results/numbers for this project.
---

# Run Benchmark

Evaluates the multi-agent pipeline against the seeded 10-issue benchmark in
`sandbox_repo/issues.yaml`, compares it to a single-shot (no agent
scaffolding) baseline using the same model, and produces a markdown report
plus a comparison chart.

## Steps

1. Run the multi-agent pipeline over every issue (no GitHub calls, fully
   local and free of side effects):

   ```bash
   source .venv/bin/activate
   python3 benchmark/run_benchmark.py
   ```

   Pass specific issue ids to run a subset, e.g.
   `python3 benchmark/run_benchmark.py B1 B2`.

2. Run the single-shot baseline over the same issues:

   ```bash
   python3 benchmark/baseline_single_shot.py
   ```

3. Generate the comparison report and chart:

   ```bash
   python3 benchmark/report.py
   ```

   Outputs: `benchmark/results/report.md` (markdown table + headline
   resolution-rate numbers) and `benchmark/results/comparison_chart.png`
   (bar chart by issue category).

## Notes

- Results are gitignored (`benchmark/results/*.json`, `*.png`) since
  they're regenerated, not source-of-truth artifacts.
- Both harnesses call the real Gemini API -- expect the full 10-issue run
  to take a few minutes and make on the order of 60-100 model calls total
  for the multi-agent side (triage + up to 3 retries of code/test/review +
  PR draft per issue).
