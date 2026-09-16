#!/usr/bin/env bash
# Reset the demo to a clean, unscored state before recording a walkthrough.
#
# Clears every lead, re-imports the sample dataset, and then stops. Enrichment
# is deliberately NOT run, so you can click "Score 13 leads" on camera and show
# the progress bar filling in.
#
# Override the defaults if you are serving the built app from the container:
#   API=http://localhost:8080 APP=http://localhost:8080 ./scripts/reset_demo.sh
set -euo pipefail

API="${API:-http://localhost:8000}"
APP="${APP:-http://localhost:5173}"

if ! curl -sf "$API/api/health" >/dev/null 2>&1; then
  echo "The API is not responding at $API"
  echo
  echo "Start it first:"
  echo "  cd backend && DEMO_MODE=true uvicorn app.main:app --reload --port 8000"
  exit 1
fi

echo "Clearing leads..."
curl -sf -X DELETE "$API/api/leads" >/dev/null

echo "Importing the sample dataset..."
added=$(curl -sf -X POST "$API/api/leads/import-sample" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['added'])")

echo "  $added leads imported, not yet scored."
echo
echo "Ready. Open: $APP"
echo "Then click \"Score $added leads\" to run enrichment on camera."
