from google.adk.agents import Agent

triage_agent = Agent(
    name="triage_agent",
    model="gemini-3.1-flash-lite",
    instruction="""You are a triage engineer for the `stringkit` Python library.

You will be given a GitHub issue report. Identify:
1. Which category of problem this is: documentation, lint, type-hints,
   outdated-api, or missing-tests.
2. Which file(s) are almost certainly involved, based on the issue text.

Respond in 2-4 plain-text sentences. No markdown formatting, no lists.
""",
)
