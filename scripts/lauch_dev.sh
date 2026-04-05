#!/usr/bin/env bash
set -euo pipefail

# Backwards-compatible alias for common typo.
# The canonical entrypoint is: ./scripts/launch_dev.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/launch_dev.sh"

