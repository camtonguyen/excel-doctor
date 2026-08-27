#!/usr/bin/env bash
# Set up agent adapters locally. Each agent gets its own config
# pointing at the shared skills/ directory.
# Run once after cloning: bash scripts/setup-agents.sh

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"

echo "Setting up agent adapters..."

# --- Antigravity (.agents/) ---
mkdir -p "$ROOT/.agents/rules"
cat > "$ROOT/.agents/rules/000-foundation.md" << 'EOF'
Read and follow @/AGENTS.md — it is the shared foundation for this project.
EOF
ln -sfn ../skills "$ROOT/.agents/skills"
echo "  .agents/ ready"

# --- Claude Code (.claude/) ---
mkdir -p "$ROOT/.claude"
cat > "$ROOT/.claude/CLAUDE.md" << 'EOF'
Read AGENTS.md.
EOF
cat > "$ROOT/.claude/settings.json" << 'EOF'
{
  "permissions": {}
}
EOF
ln -sfn ../skills "$ROOT/.claude/skills"
echo "  .claude/ ready"

# --- Codex (.codex/) ---
mkdir -p "$ROOT/.codex"
cat > "$ROOT/.codex/config.toml" << 'EOF'
# Codex adapter — points at the shared skills and prompts directories.

[skills]
path = "../skills"

[prompts]
path = "../prompts"
EOF
echo "  .codex/ ready"

echo "Done. Each agent's skills/ symlink points at the shared root skills/ directory."
