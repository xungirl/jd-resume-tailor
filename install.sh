#!/bin/sh
# One-time setup: register JD Tailor's local helper with Chrome and Edge.
#   ./install.sh            install
#   ./install.sh --uninstall
set -e
DIR="$(cd "$(dirname "$0")" && pwd -P)"
if [ "$1" = "--uninstall" ]; then exec python3 "$DIR/host/jdt.py" uninstall; fi
command -v python3 >/dev/null || { echo "python3 is needed (it comes with Xcode command line tools: xcode-select --install)"; exit 1; }
python3 "$DIR/host/jdt.py" install
echo
python3 "$DIR/host/jdt.py" doctor
