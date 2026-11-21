#!/usr/bin/env bash
# One-line install for jd-resume-tailor (any agent):
#
#   git clone https://github.com/xungirl/jd-resume-tailor ~/jd-resume-tailor && ~/jd-resume-tailor/install.sh
#
# It links the skill (it does not copy it) into the folders agents read skills from:
#   ~/.claude/skills/jd-resume-tailor   Claude Code
#   ~/.agents/skills/jd-resume-tailor   OpenAI Codex, DeepSeek Harness
# so `git pull` in the clone updates every agent at once, and the builder stays next to the skill.
#
#   ./install.sh               link for all agents (default)
#   ./install.sh --claude      Claude Code only
#   ./install.sh --agents      Codex / DeepSeek Harness only
#   ./install.sh --uninstall   remove the links this script made
#
# It writes nothing else: no config, no packages. The skill asks for your paths on first use.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd -P)"
skill="$here/skills/jd-resume-tailor"
claude_dir="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
agents_dir="${AGENTS_SKILLS_DIR:-${DSH_AGENTS_HOME:-$HOME/.agents}/skills}"

mode=all
case "${1:-}" in
  ""|--all) mode=all ;;
  --claude) mode=claude ;;
  --agents|--codex|--deepseek) mode=agents ;;
  --uninstall) mode=uninstall ;;
  -h|--help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
esac

[ -f "$skill/SKILL.md" ] || { echo "error: $skill/SKILL.md not found. Run this script from inside the cloned repo." >&2; exit 1; }

say()  { printf '%s\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }

link() {  # link <skills dir> <agent label>
  local dest="$1/jd-resume-tailor"
  mkdir -p "$1"
  if [ -L "$dest" ]; then
    ln -sfn "$skill" "$dest"; ok "$2: $dest"
  elif [ -e "$dest" ]; then
    warn "$2: skipped, $dest already exists and is not a link (an older copy? move it away and re-run)"
  else
    ln -s "$skill" "$dest"; ok "$2: $dest"
  fi
}

unlink_one() {  # unlink <skills dir> <agent label>
  local dest="$1/jd-resume-tailor"
  if [ -L "$dest" ] && [ "$(cd "$dest" 2>/dev/null && pwd -P)" = "$skill" ]; then
    rm "$dest"; ok "$2: removed $dest"
  elif [ -e "$dest" ] || [ -L "$dest" ]; then
    warn "$2: left $dest alone (not a link to this clone)"
  fi
}

if [ "$mode" = uninstall ]; then
  say "Removing jd-resume-tailor links"
  unlink_one "$claude_dir" "Claude Code"
  unlink_one "$agents_dir" "Codex / DeepSeek Harness"
  say "Done. Your bullet bank, PDFs and ~/.config/jd-resume-tailor were not touched. Delete $here to remove the code."
  exit 0
fi

say "Installing jd-resume-tailor from $here"
[ "$mode" = agents ] || link "$claude_dir" "Claude Code"
[ "$mode" = claude ] || link "$agents_dir" "Codex / DeepSeek Harness"

say ""
say "Checking what the resume builder needs"
py=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then py="$c"; break; fi
done
if [ -n "$py" ]; then ok "$("$py" --version 2>&1)"; else warn "Python 3.11 or newer not found. Install it from https://www.python.org/downloads/ (or: brew install python)"; fi
if command -v uv >/dev/null 2>&1; then
  ok "uv $(uv --version 2>/dev/null | awk '{print $2}')"
else
  warn "uv not found (optional). Install: curl -LsSf https://astral.sh/uv/install.sh | sh   — or skip it and run: ${py:-python3} -m pip install reportlab"
fi
command -v pdftoppm >/dev/null 2>&1 && ok "pdftoppm (lets the agent look at the PDF)" || say "  - pdftoppm not found (optional; on macOS: brew install poppler)"

say ""
say "Next: open Claude Code, Codex or DeepSeek Harness and say:"
say "    tailor my resume for <job posting link>"
say "On first use it asks where your resume is (a PDF or Word file is fine) and where to save PDFs."
say "Update later with: git -C \"$here\" pull      Uninstall with: \"$here/install.sh\" --uninstall"
