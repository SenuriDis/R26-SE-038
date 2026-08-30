#!/usr/bin/env bash
#
# GitHub Action entrypoint.
#
# Runs the pipeline over the checked-out repository, then hands the results to
# post_results.py, which writes the job summary and optionally comments on the
# pull request.

set -euo pipefail

WORKSPACE="${GITHUB_WORKSPACE:-/github/workspace}"
PIPELINE="/opt/pipeline"
ARTIFACTS="${WORKSPACE}/.ai-test-artifacts"

TARGET="${INPUT_PATH:-.}"
CHANGED_ONLY="${INPUT_CHANGED_ONLY:-true}"
MAX_FUNCTIONS="${INPUT_MAX_FUNCTIONS:-10}"
MIN_RISK="${INPUT_MIN_RISK_LEVEL:-MEDIUM}"

# C3 reads .env relative to its own directory. Writing the key there keeps it
# out of the workspace, which is the checked-out repository.
if [ -n "${INPUT_GROQ_API_KEY:-}" ]; then
  printf 'GROQ_API_KEY=%s\n' "${INPUT_GROQ_API_KEY}" > "${PIPELINE}/.env"
else
  echo "::error::groq-api-key was not provided. Test generation cannot run."
  exit 1
fi

cd "${WORKSPACE}"

# Actions checks out with the repository owned by a different user than the one
# running the container, and git refuses to operate on it without this. Without
# working git, history mining silently yields nothing and every function scores
# as though it were brand new.
git config --global --add safe.directory "${WORKSPACE}" || true

if ! git -C "${WORKSPACE}" rev-parse HEAD >/dev/null 2>&1; then
  echo "::warning::No git history found. Risk scores rely on it -- set fetch-depth: 0 on actions/checkout."
fi

ARGS=(
  "${TARGET}"
  --artifacts "${ARTIFACTS}"
  --min-risk-level "${MIN_RISK}"
  --stage3
  --stage4
)

if [ "${CHANGED_ONLY}" = "true" ]; then
  ARGS+=(--changed-only)
fi

if [ -n "${MAX_FUNCTIONS}" ] && [ "${MAX_FUNCTIONS}" != "0" ]; then
  ARGS+=(--max-functions "${MAX_FUNCTIONS}")
fi

echo "::group::Running the pipeline"
set +e
python "${PIPELINE}/run_pipeline.py" "${ARGS[@]}"
PIPELINE_STATUS=$?
set -e
echo "::endgroup::"

if [ "${PIPELINE_STATUS}" -ne 0 ]; then
  echo "::warning::The pipeline exited with status ${PIPELINE_STATUS}. Reporting whatever it produced."
fi

python "${PIPELINE}/action/post_results.py" \
  --artifacts "${ARTIFACTS}" \
  --pipeline-root "${PIPELINE}"
