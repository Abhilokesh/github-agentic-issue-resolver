from google.adk.agents import Agent

_INSTRUCTION_TEMPLATE = """You are a triage engineer for {project_name}.

You will be given a GitHub issue report. Identify:
1. Which category of problem this is: documentation, lint, type-hints,
   outdated-api, missing-tests, or a general code/logic bug.
2. Which file(s) are almost certainly involved, based on the issue text.

Respond in 2-4 plain-text sentences. No markdown formatting, no lists.
"""


def build_triage_agent(project_name: str) -> Agent:
    """Build a TriageAgent describing the target as `project_name`."""
    return Agent(
        name="triage_agent",
        model="gemini-3.1-flash-lite",
        instruction=_INSTRUCTION_TEMPLATE.format(project_name=project_name),
    )


# Default instance used by the benchmark/demo path.
triage_agent = build_triage_agent("the `stringkit` Python library")
