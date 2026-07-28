#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
log_file="$(mktemp)"
server_pid=""

cleanup() {
  status=$?
  trap - EXIT
  if [[ -n "$server_pid" ]]; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
  if [[ "$status" -ne 0 ]]; then
    echo "Lab API log:"
    sed -n '1,200p' "$log_file"
  fi
  rm -f "$log_file"
  exit "$status"
}
trap cleanup EXIT

cd "$repo_dir"

python3 -m py_compile lab_api.py
python3 lab_api.py >"$log_file" 2>&1 &
server_pid=$!

for _ in {1..30}; do
  if ! kill -0 "$server_pid" 2>/dev/null; then
    echo "Lab API exited before becoming healthy."
    exit 1
  fi
  if python3 -c 'import json, urllib.request; data=json.load(urllib.request.urlopen("http://127.0.0.1:8088/health")); assert data["status"] == "healthy"' 2>/dev/null; then
    break
  fi
  sleep 0.2
done

python3 -c 'import json, urllib.request; data=json.load(urllib.request.urlopen("http://127.0.0.1:8088/health")); assert data["status"] == "healthy"'

postman collection run \
  postman/tse-api-incident-lab.postman_collection.json \
  --environment postman/tse-local-lab.postman_environment.json \
  --bail

for secret in revoked-demo-key active-demo-key viewer-demo-token admin-demo-token; do
  if grep -Fq "$secret" "$log_file"; then
    echo "Secret-handling check failed: raw demo credential appeared in server logs."
    exit 1
  fi
done

echo "Verification complete: collection passed and server logs contain no raw credentials."
