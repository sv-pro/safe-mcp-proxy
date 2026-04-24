#!/usr/bin/env bash
# Generate demo GIFs from VHS tape files.
# Requires: https://github.com/charmbracelet/vhs
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "Generating injection.gif …"
vhs docs/demo/injection.tape
echo "Generating absent.gif …"
vhs docs/demo/absent.tape
echo "Done. GIFs written to docs/demo/"
