#!/bin/bash
# RUNS=<dir> drive.sh base-a skill-a ...: one claude -p run per arg, one at a time, in $RUNS/<r>
# (built by setup_run.py). MODEL overrides the model (default claude-opus-5-5). Output: $RUNS/<r>.json (result, duration_ms), $RUNS/<r>.diff
E=$(dirname "$(readlink -f "$0")")
RUNS=${RUNS:-/tmp/write-test-004}
for r in "$@"; do
  arm=${r%-*}; t=${r#*-}
  cd "$RUNS/$r" || continue
  claude -p "$(python3 $E/prompts.py $arm $t)" --model "${MODEL:-claude-opus-5-5}" --mcp-config .mcp.json \
    --permission-mode acceptEdits \
    --allowedTools "mcp__godot__*" "Bash(godot:*)" "Bash(git status:*)" "Bash(git diff:*)" "Bash(ls:*)" "Bash(grep:*)" "Bash(uv:*)" \
    --output-format json > "$RUNS/$r.json" 2> "$RUNS/$r.err"
  git add -N . && git diff > "$RUNS/$r.diff"
  python3 -c "import json; d=json.load(open('$RUNS/$r.json')); print('$r', d.get('duration_ms'), d.get('num_turns'), d.get('is_error'))"
done
