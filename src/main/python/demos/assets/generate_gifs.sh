#!/usr/bin/env bash
# Generate demo GIFs from VHS tape files.
# Requires: https://github.com/charmbracelet/vhs
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "Generating injection.gif …"
vhs demos/assets/tapes/injection.tape
echo "Generating absent.gif …"
vhs demos/assets/tapes/absent.tape
echo "Done. GIFs written to demos/assets/"
