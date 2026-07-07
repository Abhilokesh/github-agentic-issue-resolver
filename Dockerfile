# Documented deployability path -- see README for the honest caveat: this
# has not been built/run in the dev environment used for this project
# (no Docker available there), but it follows the standard, low-risk
# pattern for a Python + ADK agent and is meant to be built/run wherever
# Docker/Cloud Run actually is available.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ ./agent/
COPY sandbox_repo/ ./sandbox_repo/
COPY benchmark/ ./benchmark/
COPY .agents/ ./.agents/
COPY scripts/setup_github_mcp.sh ./scripts/setup_github_mcp.sh
RUN chmod +x ./scripts/setup_github_mcp.sh && ./scripts/setup_github_mcp.sh

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# Demo-mode CLI is the default entrypoint; override CMD to run the
# benchmark harness instead (`python3 -m benchmark.run_benchmark`).
ENTRYPOINT ["python3", "-m", "agent.cli"]
CMD ["--help"]
