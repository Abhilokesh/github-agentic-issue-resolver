---
name: resolve-github-issue
description: Run the multi-agent pipeline (triage, code, sandboxed test, review, PR draft) against one issue from sandbox_repo/issues.yaml. Use when asked to resolve, fix, or work on a specific seeded issue by its id (e.g. "resolve issue B1").
---

# Resolve GitHub Issue

Resolves a single issue from `sandbox_repo/issues.yaml` end to end: triage,
write a patch, run it in the ephemeral sandbox against the issue's oracle
check, get it code-reviewed, and (if approved) draft a PR description.

This never opens a real pull request on its own -- PR creation always
requires a human to explicitly approve via `agent/cli.py`.

## Steps

1. Make sure dependencies are installed and `.env` has `GEMINI_API_KEY` set
   (see `.env.example`).
2. To resolve one issue and just see the result (no PR, no GitHub calls):

   ```bash
   source .venv/bin/activate
   python3 -c "
   import asyncio, yaml, json
   from agent.coordinator import run_for_issue
   issue = next(i for i in yaml.safe_load(open('sandbox_repo/issues.yaml'))['issues'] if i['id'] == '<ISSUE_ID>')
   print(json.dumps(asyncio.run(run_for_issue(issue)), indent=2, default=str))
   "
   ```

3. To resolve an issue AND go through the human-approval gate before
   opening a real PR on the configured `SANDBOX_REPO`:

   ```bash
   python3 -m agent.cli resolve --issue-id <ISSUE_ID>
   ```

   This will print the patch, test result, and review verdict, then pause
   for an explicit `y/N` confirmation before calling the GitHub MCP
   server's `create_pull_request` tool.

## Notes

- Valid issue ids are listed in `sandbox_repo/issues.yaml` (A1, A2, B1, B2,
  C1, C2, D1, D2, E1, E2).
- If a run is rate-limited by the Gemini API, it will back off and retry
  automatically (see `agent/tools/llm_backoff.py`) -- this is expected
  behavior, not a failure.
