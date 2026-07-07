#!/usr/bin/env bash
# Documented Cloud Run deployment path -- NOT executed as part of this
# project's build (no GCP billing account was active in the dev
# environment). Run this yourself once billing is set up on your project.
#
# Requires: gcloud CLI authenticated, an active GCP project with billing
# enabled and the Cloud Run + Artifact Registry APIs enabled, and
# GEMINI_API_KEY / GITHUB_PERSONAL_ACCESS_TOKEN / SANDBOX_REPO set as real
# values (passed as Cloud Run secrets/env vars below, never baked into the
# image).
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT first}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-github-issue-agent}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

gcloud config set project "$PROJECT_ID"

gcloud builds submit "$REPO_ROOT" \
  --tag "gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

gcloud run deploy "$SERVICE_NAME" \
  --image "gcr.io/${PROJECT_ID}/${SERVICE_NAME}" \
  --region "$REGION" \
  --no-allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},OTEL_EXPORT_TARGET=gcp" \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,GITHUB_PERSONAL_ACCESS_TOKEN=github-pat:latest"

echo "Deployed. Create the referenced secrets first with:"
echo "  gcloud secrets create gemini-api-key --data-file=-  <<< \"\$GEMINI_API_KEY\""
echo "  gcloud secrets create github-pat --data-file=-      <<< \"\$GITHUB_PERSONAL_ACCESS_TOKEN\""
