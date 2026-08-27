#!/usr/bin/env bash
# Install git hooks for Excel Doctor.
# Run once after cloning: bash scripts/install-hooks.sh

set -euo pipefail

HOOKS_DIR="$(git rev-parse --show-toplevel)/.git/hooks"
mkdir -p "$HOOKS_DIR"

# commit-msg — reject banned trailers and attribution
cat > "$HOOKS_DIR/commit-msg" << 'EOF'
#!/usr/bin/env bash
grep -qiE '(^co-authored-by|generated with|🤖|noreply@anthropic)' "$1" && {
  echo "commit message contains a banned trailer or attribution"; exit 1; }
exit 0
EOF
chmod +x "$HOOKS_DIR/commit-msg"

# pre-commit — no direct commits to main
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/usr/bin/env bash
[ "$(git symbolic-ref --short HEAD)" = "main" ] && {
  echo "commit to a branch, not main"; exit 1; }
exit 0
EOF
chmod +x "$HOOKS_DIR/pre-commit"

echo "Hooks installed to $HOOKS_DIR"
