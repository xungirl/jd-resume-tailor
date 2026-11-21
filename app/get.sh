#!/bin/sh
# Install or update JD Resume Tailor, then show how to use it:
#
#   curl -fsSL https://raw.githubusercontent.com/xungirl/jd-resume-tailor/main/app/get.sh | sh
#
# Safe to run again: it updates the clone (fast-forward only), registers the browser helper again,
# and changes nothing else. Never uses sudo, never installs system packages.
# Overrides, mostly for testing: JDRT_DIR (default ~/jd-resume-tailor), JDRT_REPO, JDRT_BRANCH.

# Everything is inside main, called on the last line, so a half-downloaded script runs nothing.
main() {
  set -eu
  repo="${JDRT_REPO:-https://github.com/xungirl/jd-resume-tailor.git}"
  dir="${JDRT_DIR:-$HOME/jd-resume-tailor}"
  branch="${JDRT_BRANCH:-}"

  command -v git >/dev/null 2>&1 || die "git is needed. On a Mac: xcode-select --install"
  command -v python3 >/dev/null 2>&1 || die "python3 is needed. On a Mac: xcode-select --install"
  python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' </dev/null \
    || die "Python 3.9 or newer is needed (found $(python3 -V 2>&1))"

  if [ -d "$dir/.git" ]; then
    say "Updating $dir"
    git -C "$dir" pull --ff-only -q </dev/null \
      || say "  Could not update it (local changes, or no network). Using it as it is."
  elif [ -e "$dir" ]; then
    die "$dir exists but is not a git clone. Move it aside, or set JDRT_DIR to another folder."
  else
    say "Downloading to $dir"
    if [ -n "$branch" ]; then
      git clone -q -b "$branch" "$repo" "$dir" </dev/null
    else
      git clone -q "$repo" "$dir" </dev/null
    fi
  fi
  [ -f "$dir/app/host/jdt.py" ] || die "$dir has no app/host/jdt.py. Is it the jd-resume-tailor repo, and up to date?"

  if ! command -v pdftotext >/dev/null 2>&1; then
    say ""
    say "poppler is missing. The script checks read the PDF with it, so install it:"
    case "$(uname -s)" in
      Darwin) say "  brew install poppler" ;;
      *) say "  your package manager's poppler-utils (for example: apt install poppler-utils)" ;;
    esac
  fi

  say ""
  # Registers the helper with Chrome and Edge if they're installed; does nothing harmful if not.
  sh "$dir/app/install.sh" </dev/null || say "(Registering with Chrome/Edge didn't work. The browser version below doesn't need it.)"

  say ""
  say "Ready. Two ways to use it:"
  say ""
  say "  1. In any browser, Safari too:"
  say "       $dir/app/jdrt web"
  say "     (the same as: python3 $dir/app/host/jdt.py web). It opens a page on this computer only."
  say ""
  say "  2. As a Chrome or Edge extension: open chrome://extensions, turn on Developer mode,"
  say "     click Load unpacked, and pick $dir/app/extension"
  say ""
  say "First time? Run the jd-resume-tailor skill once in Claude Code, so it learns where your bullet bank is."
}

say() { printf '%s\n' "$*"; }
die() { printf 'jd-resume-tailor: %s\n' "$*" >&2; exit 1; }

main "$@"
