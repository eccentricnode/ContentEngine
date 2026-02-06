#!/bin/bash
set -e

MAX_ITERATIONS=${1:-25}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🚀 Starting Ralph on Content Engine - Phase 3 Semantic Blueprints"
echo "📁 Project: $PROJECT_ROOT"
echo "🔄 Max iterations: $MAX_ITERATIONS"

cd "$PROJECT_ROOT"

for i in $(seq 1 $MAX_ITERATIONS); do
  echo ""
  echo "═══════════════════════════════════════════"
  echo "Iteration $i/$MAX_ITERATIONS"
  echo "═══════════════════════════════════════════"

  OUTPUT=$(cat "$SCRIPT_DIR/prompt.md" \
    | claude --dangerously-skip-permissions \
    --model sonnet 2>&1 | tee /dev/stderr) || true

  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo ""
    echo "✅ All stories complete! Phase 3 Semantic Blueprints implemented!"
    exit 0
  fi

  sleep 2
done

echo ""
echo "⚠️ Max iterations reached"
exit 1
