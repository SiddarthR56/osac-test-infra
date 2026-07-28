#!/usr/bin/env bash
# redeploy-server.sh — Runs ON the bare-metal server. Executes the full deploy
# pipeline step-by-step with progress tracking.
#
# If a step fails, fix the issue and re-run this script; completed steps are
# automatically skipped. Delete /root/.deploy-progress to force a fresh start.
#
# Steps: setup → deploy-lab → deploy-ocp-snapshot → setup-caas → deploy-caas → post-install
#
# Usage (on server): make redeploy-fresh
# Usage (from laptop): make deploy-jump  (calls this script via tmux)
set -euo pipefail

PROGRESS_FILE="${DEPLOY_PROGRESS_FILE:-/root/.deploy-progress}"
EXTRA_VARS="${1:-}"

STEPS=(
    setup
    deploy-lab
    deploy-ocp-snapshot
    setup-caas
    deploy-caas
    post-install
)

touch "$PROGRESS_FILE"

for step in "${STEPS[@]}"; do
    if grep -qxF "$step" "$PROGRESS_FILE" 2>/dev/null; then
        echo "=== SKIP $step (already completed) ==="
        continue
    fi

    echo ""
    echo "========================================"
    echo "  Running: make $step"
    echo "========================================"
    echo ""

    if make "$step" ${EXTRA_VARS:+EXTRA_VARS="${EXTRA_VARS}"}; then
        echo "$step" >> "$PROGRESS_FILE"
        echo "=== DONE $step ==="
    else
        echo ""
        echo "========================================"
        echo "  FAILED at: $step"
        echo "  Fix the issue and re-run this script."
        echo "  Progress saved to: $PROGRESS_FILE"
        echo "========================================"
        exit 1
    fi
done

echo ""
echo "========================================"
echo "  Full deploy completed successfully!"
echo "========================================"
rm -f "$PROGRESS_FILE"
