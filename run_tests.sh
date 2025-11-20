#!/usr/bin/env bash
set -euo pipefail

# One‑liner: bash run_tests.sh [pytest args]
# - Uses your local venv if present
# - Installs test deps on first run (requirements_test*.txt)
# - Runs the Public Transport tests if they exist, otherwise runs picked tests

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Ensure pytest is available; install minimal test deps if not
if ! python - <<'PY'
import importlib
raise SystemExit(0 if importlib.util.find_spec('pytest') else 1)
PY
then
  echo "Installing test dependencies …"
  if [[ -f requirements_test_all.txt ]]; then
    pip install -r requirements_test_all.txt -r requirements.txt
  elif [[ -f requirements_test.txt ]]; then
    pip install -r requirements_test.txt -r requirements.txt
  else
    pip install pytest
  fi
fi

# Pick targets
TARGETS=()
if [[ -d tests/components/public_transport ]]; then
  TARGETS+=(tests/components/public_transport)
elif rg -n "public_transport" tests >/dev/null 2>&1; then
  TARGETS+=(tests)
else
  # Fallback: run all tests (can be slow)
  TARGETS+=(tests)
fi

echo "Running pytest on: ${TARGETS[*]}"
pytest "${TARGETS[@]}" \
  --durations-min=1 --durations=0 \
  "$@"

