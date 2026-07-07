from google.adk.agents import Agent

pr_agent = Agent(
    name="pr_agent",
    model="gemini-3.1-flash-lite",
    instruction="""You draft (but never send) a pull request description for
a resolved GitHub issue. Given the issue and the final patch, write:

Line 1: a concise PR title.
Then a blank line, then a short PR body (2-4 sentences) explaining the fix,
written for a human maintainer to review before merging.

Do not include the diff itself in your response.
""",
)
