#!/usr/bin/env bash
# Keeps the Backstage app's bundled catalog fixture in sync with the
# canonical component definition at src/4-idp/backstage/catalog-info.yaml.
# Run this before building the backend image.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANONICAL_FILE="$SCRIPT_DIR/../catalog-info.yaml"
TARGET_FILE="$SCRIPT_DIR/examples/entities.yaml"

{
  echo "---"
  echo "# Canonical source: src/4-idp/backstage/catalog-info.yaml (synced by"
  echo "# scripts/sync-catalog.sh before each image build). Describes the"
  echo "# existing todo-api Deployment in the \`todo\` namespace."
  cat "$CANONICAL_FILE"
} > "$TARGET_FILE"

echo "Synced $CANONICAL_FILE -> $TARGET_FILE"
