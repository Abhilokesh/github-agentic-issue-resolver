---
name: lint-and-test-patch
description: Run a candidate unified diff through the same slopsquatting guard and ephemeral sandbox the agent pipeline uses, without going through the LLM agents. Use when asked to check, validate, lint, or test a patch/diff against the sandbox repo before applying it for real.
---

# Lint and Test a Patch

Runs one candidate patch through the exact same checks the CodingAgent's
output goes through: the no-new-dependencies guard, then applying it to a
fresh ephemeral copy of `sandbox_repo/` and running a given oracle command.
Useful for debugging a failing issue, or for validating a new seeded issue
you're adding to `sandbox_repo/issues.yaml`.

## Steps

1. Have your unified diff as a file, e.g. `/tmp/candidate.patch` (must be
   `git diff`-format: `diff --git a/... b/...`, `---`/`+++` headers, `@@`
   hunks).
2. Run:

   ```bash
   source .venv/bin/activate
   python3 -c "
   import json
   from agent.tools.sandbox_exec import run_in_sandbox
   patch = open('/tmp/candidate.patch').read()
   oracle_cmd = '<the oracle_cmd from issues.yaml for the issue you are testing>'
   print(json.dumps(run_in_sandbox(patch, oracle_cmd), indent=2))
   "
   ```

3. Read the result:
   - `guard_passed: false` -- rejected before testing (new dependency or
     edited a dependency file); see `guard_reason`.
   - `applied: false` -- the diff didn't apply cleanly; see `apply_error`.
     A missing trailing newline or markdown code fences are the most
     common causes -- `agent/tools/patch_tools.py::normalize_patch_text`
     already strips both, so this usually means the diff's hunk headers
     or context lines don't actually match the target file's current
     content.
   - `oracle_passed: false` -- applied cleanly but the check still fails;
     see `stdout`/`stderr` for the real error.

## Notes

- This never touches `sandbox_repo/` itself -- every call works on a fresh
  `tempfile.mkdtemp()` copy that's deleted afterward (ephemeral sandbox).
- The sandboxed process runs with a scrubbed environment (no API keys/
  tokens) and CPU/memory/time limits -- see `agent/tools/sandbox_exec.py`
  for the exact limits and the documented isolation tradeoffs.
