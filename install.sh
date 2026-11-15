#!/usr/bin/env bash
# Link the skill into Claude Code's personal skills folder.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/jd-resume-tailor"
mkdir -p "$(dirname "$dest")"
if [ -e "$dest" ] && [ ! -L "$dest" ]; then
  echo "$dest exists and is not a link; move it away first" >&2; exit 1
fi
ln -sfn "$here/skills/jd-resume-tailor" "$dest"
echo "linked $dest -> $here/skills/jd-resume-tailor"
mkdir -p "$HOME/.config/jd-resume-tailor"
if [ ! -f "$HOME/.config/jd-resume-tailor/config.md" ]; then
  cp "$here/config.example.md" "$HOME/.config/jd-resume-tailor/config.md"
  echo "wrote ~/.config/jd-resume-tailor/config.md: edit the paths in it"
fi
