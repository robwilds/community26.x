#!/bin/bash
set -euo pipefail

if [ ! -f docker-compose.yaml ]; then
  echo "ERROR: Run this from the project root (where docker-compose.yaml lives)" >&2
  exit 1
fi

echo "Starting Alfresco Control Plane..."
python3 mgr/server.py &
SERVER_PID=$!

echo -n "Waiting for server"
for i in $(seq 1 30); do
  if curl -sf http://localhost:9700 >/dev/null 2>&1; then
    echo " ready."
    open http://localhost:9700
    break
  fi
  echo -n "."
  sleep 1
done

wait "$SERVER_PID"
