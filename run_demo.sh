#!/usr/bin/env bash
set -euo pipefail

# One‑terminal launcher: starts the GTFS‑RT demo feed and Home Assistant.
# Usage: bash run_demo.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -d "$ROOT_DIR/.venv" ]]; then
  # Activate local venv if present
  # shellcheck source=/dev/null
  source "$ROOT_DIR/.venv/bin/activate"
fi

FEED_SCRIPT="$ROOT_DIR/demo_data/public_transport_demo/run_fake_gtfs_rt.py"
if [[ ! -f "$FEED_SCRIPT" ]]; then
  echo "ERROR: GTFS-RT demo script not found at: $FEED_SCRIPT" >&2
  echo "Hint: Path is demo_data/public_transport_demo/run_fake_gtfs_rt.py" >&2
  exit 1
fi

cleanup() {
  if [[ -n "${FEED_PID:-}" ]] && kill -0 "$FEED_PID" 2>/dev/null; then
    echo "Stopping GTFS-RT demo (pid $FEED_PID)"
    kill "$FEED_PID" 2>/dev/null || true
    wait "$FEED_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "Starting GTFS-RT demo feed …"
python "$FEED_SCRIPT" >"$ROOT_DIR/.feed.log" 2>&1 &
FEED_PID=$!

# Wait for the feed to become reachable
for _ in {1..30}; do
  if curl -sI http://localhost:8081/gtfs-rt/TripUpdates.pb >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

echo "Feed URL:   http://localhost:8081/gtfs-rt/TripUpdates.pb"
echo "Dashboard:  http://localhost:8123"
echo "Config dir: $ROOT_DIR/config"
echo "Logs:       $ROOT_DIR/.feed.log"
echo
echo "Launching Home Assistant (Ctrl+C to stop) …"
hass -c "$ROOT_DIR/config"

