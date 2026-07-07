from pathlib import Path

from google.adk.agents import Agent

from ..tools.repo_read import SANDBOX_REPO, make_read_repo_file_tool

_INSTRUCTION_TEMPLATE = """You are a careful software engineer fixing ONE narrowly
scoped GitHub issue in {project_name}.

Rules:
- Use the `read_repo_file` tool to read the CURRENT content of any file you
  plan to change before writing a diff. Never guess file contents.
- Make the SMALLEST possible change that resolves the issue. Do not refactor
  unrelated code, do not add new dependencies, do not edit
  requirements.txt/pyproject.toml, do not delete or rewrite unrelated tests.
- Your entire final response must be ONLY a valid unified diff (`git diff`
  format: `diff --git a/... b/...`, `---`/`+++` headers, `@@` hunks). No
  markdown code fences, no explanation before or after the diff.
- Diffs must apply cleanly against the file content exactly as returned by
  `read_repo_file` -- always re-read a file before patching it, even on a
  retry, since your patch is applied fresh each attempt.
- If you are given feedback from a previous failed attempt (a test failure,
  an apply error, or review comments), address exactly what it describes.
"""


def build_coding_agent(project_name: str, repo_root: Path) -> Agent:
    """Build a CodingAgent scoped to `repo_root`, describing the target as
    `project_name` in its instructions (e.g. "the `stringkit` Python
    library", or "the owner/repo GitHub repository")."""
    return Agent(
        name="coding_agent",
        model="gemini-3.1-flash-lite",
        instruction=_INSTRUCTION_TEMPLATE.format(project_name=project_name),
        tools=[make_read_repo_file_tool(repo_root)],
    )


# Default instance used by the benchmark/demo path.
coding_agent = build_coding_agent("the `stringkit` Python library", SANDBOX_REPO)
